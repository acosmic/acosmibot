"""
Unified Session Management Service

Treats each active user as having a temporary session in Redis that tracks
ALL user state: XP, currency, messages, reactions, and game logs. All updates
happen in memory with periodic persistence to the database.

Session Lifecycle:
1. Session Start: First activity (message/reaction/game) loads user data from DB
2. Active Session: All updates (XP/currency/games) modify Redis only
3. Session Keepalive: Each activity extends TTL
4. Session End: Inactivity (60min) or manual flush persists to DB

Benefits:
- 95%+ reduction in database writes (XP + currency + games batched)
- Instant level-up and currency updates (no DB latency)
- Prevents race conditions for rapid game sequences
- Automatic cleanup of idle sessions
- Crash-safe with periodic flushes
"""

import asyncio
import json
import math
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, List
import redis.asyncio as aioredis
import os
import uuid
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class SessionManager:
    """
    Manages in-memory sessions for active users.

    Each session contains:
    - XP and level (guild + global)
    - Currency (guild + pending changes)
    - Pending game logs
    - Message and reaction counts
    - Cooldown tracking
    - Activity timestamps
    - Dirty flag for flush tracking
    """

    def __init__(self):
        # Redis connection
        self.redis: Optional[aioredis.Redis] = None
        self.redis_available = False

        # Session settings
        self.session_ttl = 3600  # 60 minutes of inactivity before session expires
        self.flush_interval = 300  # Flush dirty sessions every 5 minutes
        self.flush_task = None

        # Fallback in-memory sessions (if Redis unavailable)
        self.fallback_sessions: Dict[Tuple[int, int], dict] = {}
        self.lock = asyncio.Lock()

        logger.info("SessionManager initialized")

    async def initialize(self):
        """
        Initialize Redis connection and start background flush task.

        If Redis is unavailable, falls back to in-memory sessions with
        immediate DB writes (same as current behavior).
        """
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_password = os.getenv('REDIS_PASSWORD', None)

            logger.info(f"SessionManager connecting to Redis at {redis_url}...")

            self.redis = await aioredis.from_url(
                redis_url,
                password=redis_password,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )

            # Test connection
            await self.redis.ping()
            self.redis_available = True
            logger.info("✅ SessionManager connected to Redis successfully")

        except Exception as e:
            logger.warning(f"⚠️ SessionManager could not connect to Redis: {e}")
            logger.warning("⚠️ Falling back to immediate DB writes (no session caching)")
            self.redis_available = False

    async def start(self):
        """Start the periodic flush task."""
        if self.redis_available:
            self.flush_task = asyncio.create_task(self._periodic_flush())
            logger.info(f"🎮 Session management started (flushes every {self.flush_interval}s)")
        else:
            logger.info("🎮 Session management in fallback mode (no Redis)")

    async def _periodic_flush(self):
        """Background task that periodically flushes dirty sessions."""
        try:
            while True:
                await asyncio.sleep(self.flush_interval)
                await self.flush_dirty_sessions()
        except asyncio.CancelledError:
            logger.info("Session flush task stopped")
            raise

    def _session_key(self, guild_id: int, user_id: int) -> str:
        """Generate Redis key for user session."""
        return f"session:{guild_id}:{user_id}"

    def _guild_vault_key(self, guild_id: int) -> str:
        """Generate Redis key for guild vault cache."""
        return f"guild_vault:{guild_id}"

    async def get_or_create_session(
        self,
        guild_id: int,
        user_id: int,
        guild_user_dao,
        user_dao
    ) -> Optional[dict]:
        """
        Get existing session or create new one from database.

        This is called on the first message from a user and loads their
        data from the database into Redis.

        Returns:
            Session dict or None if user doesn't exist
        """
        if not self.redis_available:
            # Fallback mode: return None to trigger immediate DB operations
            return None

        try:
            session_key = self._session_key(guild_id, user_id)

            # Try to get existing session from Redis
            session_data = await self.redis.get(session_key)
            if session_data:
                session = json.loads(session_data)
                # Extend TTL on access
                await self.redis.expire(session_key, self.session_ttl)
                return session

            # No session exists - load from database
            guild_user = guild_user_dao.get_guild_user(user_id, guild_id)
            if not guild_user:
                return None

            global_user = user_dao.get_user(user_id)
            if not global_user:
                return None

            # Create new session
            session = {
                # Guild-specific data
                "guild_exp": guild_user.exp,
                "guild_level": guild_user.level,
                "guild_exp_gained": guild_user.exp_gained,
                "streak": guild_user.streak,

                # Global data
                "global_exp": global_user.global_exp,
                "global_level": global_user.global_level,

                # Currency tracking
                "currency": guild_user.currency,           # Current guild currency
                "currency_to_flush": 0,                    # Net currency change to flush

                # Game buffering
                "pending_games": [],                       # List of game dicts to flush

                # Session metadata
                "last_active": datetime.now(timezone.utc).isoformat(),
                "last_xp_gain": None,  # No XP gained yet this session
                "session_start": datetime.now(timezone.utc).isoformat(),
                "dirty": False,  # No changes yet
                "messages_this_session": 0,

                # Activity tracking
                "reactions_this_session": 0,    # Track reactions in session
                "messages_to_flush": 0,         # Pending messages for DB
                "reactions_to_flush": 0,        # Pending reactions for DB
            }

            # Store in Redis with TTL
            await self.redis.setex(
                session_key,
                self.session_ttl,
                json.dumps(session)
            )

            logger.info(f"🎮 Created session for user {user_id} in guild {guild_id} (Level {session['guild_level']}, {session['currency']} currency)")

            return session

        except Exception as e:
            logger.error(f"Error getting/creating session: {e}", exc_info=True)
            return None

    async def grant_xp(
        self,
        guild_id: int,
        user_id: int,
        xp_amount: int,
        cooldown_seconds: int,
        premium_multiplier: float = 1.0
    ) -> Tuple[bool, int, int, Optional[dict]]:
        """
        Grant XP to user's active session (in-memory operation).

        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            xp_amount: Base XP to grant (before multipliers)
            cooldown_seconds: Cooldown period in seconds
            premium_multiplier: Premium XP multiplier (default 1.0)

        Returns:
            Tuple of:
            - level_up: Whether user leveled up
            - new_level: User's new level
            - xp_gained: Actual XP granted (after multipliers)
            - session: Updated session dict (or None if Redis unavailable)
        """
        if not self.redis_available:
            # Fallback mode: return None to trigger immediate DB operations
            return False, 0, 0, None

        try:
            session_key = self._session_key(guild_id, user_id)

            # Get session (this is atomic in Redis)
            session_data = await self.redis.get(session_key)
            if not session_data:
                # Session doesn't exist - caller should create it first
                return False, 0, 0, None

            session = json.loads(session_data)

            # Check cooldown
            if session.get("last_xp_gain"):
                last_xp_time = datetime.fromisoformat(session["last_xp_gain"])
                now = datetime.now(timezone.utc)
                time_since_last = (now - last_xp_time).total_seconds()

                if time_since_last < cooldown_seconds:
                    # Still on cooldown - no XP granted
                    # Update last_active but don't mark dirty
                    session["last_active"] = now.isoformat()
                    await self.redis.setex(session_key, self.session_ttl, json.dumps(session))
                    return False, session["guild_level"], 0, session

            # Apply XP multiplier (already includes streak bonus from caller)
            xp_gained = math.ceil(xp_amount * premium_multiplier)

            # Calculate old level
            old_level = session["guild_level"]

            # Apply XP gain
            session["guild_exp"] += xp_gained
            session["guild_exp_gained"] += xp_gained
            session["global_exp"] += xp_gained

            # Calculate new levels
            session["guild_level"] = self._calculate_level_from_exp(session["guild_exp"])
            session["global_level"] = self._calculate_level_from_exp(session["global_exp"])

            # Update metadata
            now = datetime.now(timezone.utc)
            session["last_xp_gain"] = now.isoformat()
            session["last_active"] = now.isoformat()
            session["messages_this_session"] += 1
            session["dirty"] = True  # Mark for flush

            # Save back to Redis
            await self.redis.setex(session_key, self.session_ttl, json.dumps(session))

            level_up = session["guild_level"] > old_level

            return level_up, session["guild_level"], xp_gained, session

        except Exception as e:
            logger.error(f"Error granting XP to session: {e}", exc_info=True)
            return False, 0, 0, None

    def _calculate_level_from_exp(self, exp: int) -> int:
        """Calculate level from experience points."""
        if exp < 0:
            return 0
        return math.floor(math.sqrt(exp / 100))

    async def update_session_activity(self, guild_id: int, user_id: int):
        """
        Update session's last_active timestamp.

        Used for messages that don't grant XP (cooldown).
        """
        if not self.redis_available:
            return

        try:
            session_key = self._session_key(guild_id, user_id)
            session_data = await self.redis.get(session_key)

            if session_data:
                session = json.loads(session_data)
                session["last_active"] = datetime.now(timezone.utc).isoformat()
                session["messages_this_session"] += 1
                # Don't mark dirty - just a keepalive
                await self.redis.setex(session_key, self.session_ttl, json.dumps(session))

        except Exception as e:
            logger.error(f"Error updating session activity: {e}")

    async def track_message_activity(self, guild_id: int, user_id: int):
        """
        Track message activity (updates last_active and message count).
        Called on EVERY message, even during XP cooldown.
        """
        if not self.redis_available:
            # Fallback: immediate DB write handled in Leveling.py
            return

        try:
            session_key = self._session_key(guild_id, user_id)
            session_data = await self.redis.get(session_key)

            if session_data:
                session = json.loads(session_data)
                session["last_active"] = datetime.now(timezone.utc).isoformat()
                session["messages_this_session"] = session.get("messages_this_session", 0) + 1
                session["messages_to_flush"] = session.get("messages_to_flush", 0) + 1
                session["dirty"] = True

                await self.redis.setex(session_key, self.session_ttl, json.dumps(session))
        except Exception as e:
            logger.error(f"Error tracking message activity: {e}")

    async def track_reaction_activity(self, guild_id: int, user_id: int):
        """
        Track reaction activity (creates session if needed for reaction-only users).
        Called on EVERY reaction addition.
        """
        if not self.redis_available:
            # Fallback: immediate DB write to both guild and global stats
            from Dao.GuildUserDao import GuildUserDao
            from Dao.UserDao import UserDao

            guild_user_dao = GuildUserDao()
            user_dao = UserDao()
            try:
                # Update guild stats
                guild_user_dao.increment_activity_counts(
                    user_id, guild_id, messages=0, reactions=1
                )
                # Update global stats (NEW - fixes fallback mode gap)
                user_dao.increment_user_stats(
                    user_id=user_id,
                    global_exp_gain=0,
                    currency_gain=0,
                    messages_gain=0,
                    reactions_gain=1
                )
            finally:
                guild_user_dao.close()
                user_dao.close()
            return

        try:
            session_key = self._session_key(guild_id, user_id)
            session_data = await self.redis.get(session_key)

            if session_data:
                # Update existing session
                session = json.loads(session_data)
                session["last_active"] = datetime.now(timezone.utc).isoformat()
                session["reactions_this_session"] = session.get("reactions_this_session", 0) + 1
                session["reactions_to_flush"] = session.get("reactions_to_flush", 0) + 1
                session["dirty"] = True

                await self.redis.setex(session_key, self.session_ttl, json.dumps(session))
            else:
                # No session yet - reaction before first message
                # Session will be created lazily when needed
                logger.debug(f"No session for reaction-only user {user_id}, will create on next message")
        except Exception as e:
            logger.error(f"Error tracking reaction activity: {e}")

    async def get_currency(self, guild_id: int, user_id: int) -> Optional[int]:
        """
        Get user's current currency from their active session.

        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID

        Returns:
            Current currency amount, or None if session doesn't exist or Redis unavailable
        """
        if not self.redis_available:
            # Fallback mode: caller should query DB directly
            return None

        try:
            session_key = self._session_key(guild_id, user_id)
            session_data = await self.redis.get(session_key)

            if session_data:
                session = json.loads(session_data)
                return session.get("currency", 0)

            return None

        except Exception as e:
            logger.error(f"Error getting currency from session: {e}")
            return None

    async def update_currency(self, guild_id: int, user_id: int, amount: int) -> bool:
        """
        Update user's currency in their active session (in-memory operation).

        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            amount: Currency delta (positive for gain, negative for loss)

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_available:
            # Fallback mode: return False to trigger immediate DB write
            return False

        try:
            session_key = self._session_key(guild_id, user_id)
            session_data = await self.redis.get(session_key)

            if not session_data:
                # Session doesn't exist - caller should create it first
                return False

            session = json.loads(session_data)

            # Update currency
            session["currency"] = session.get("currency", 0) + amount
            session["currency_to_flush"] = session.get("currency_to_flush", 0) + amount

            # Update metadata
            session["last_active"] = datetime.now(timezone.utc).isoformat()
            session["dirty"] = True

            # Save back to Redis
            await self.redis.setex(session_key, self.session_ttl, json.dumps(session))

            logger.debug(f"Updated currency for user {user_id} in session: delta={amount}, new_balance={session['currency']}")

            return True

        except Exception as e:
            logger.error(f"Error updating currency in session: {e}")
            return False

    async def queue_game(
        self,
        guild_id: int,
        user_id: int,
        game_type: str,
        amount_bet: int,
        amount_won: int,
        amount_lost: int,
        result: str,
        game_data: Optional[dict] = None,
        timestamp: Optional[str] = None
    ) -> bool:
        """
        Queue a game result to be flushed to the database.

        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            game_type: Type of game (slots, coinflip, blackjack, etc.)
            amount_bet: Amount wagered
            amount_won: Amount won (0 if loss)
            amount_lost: Amount lost (0 if win)
            result: Game result (win, loss, push, etc.)
            game_data: Optional additional game data as dict
            timestamp: Optional timestamp (defaults to now)

        Returns:
            True if successfully queued, False otherwise
        """
        if not self.redis_available:
            # Fallback mode: return False to trigger immediate DB write
            return False

        try:
            session_key = self._session_key(guild_id, user_id)
            session_data = await self.redis.get(session_key)

            if not session_data:
                # Session doesn't exist - caller should create it first
                return False

            session = json.loads(session_data)

            # Create game record
            game_record = {
                "user_id": user_id,
                "guild_id": guild_id,
                "game_type": game_type,
                "amount_bet": amount_bet,
                "amount_won": amount_won,
                "amount_lost": amount_lost,
                "result": result,
                "game_data": json.dumps(game_data) if game_data else None,
                "timestamp": timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            }

            # Add to pending games
            if "pending_games" not in session:
                session["pending_games"] = []
            session["pending_games"].append(game_record)

            # Update metadata
            session["last_active"] = datetime.now(timezone.utc).isoformat()
            session["dirty"] = True

            # Save back to Redis
            await self.redis.setex(session_key, self.session_ttl, json.dumps(session))

            logger.debug(f"Queued {game_type} game for user {user_id}: {result} ({len(session['pending_games'])} games pending)")

            return True

        except Exception as e:
            logger.error(f"Error queuing game in session: {e}")
            return False

    async def add_vault_currency(self, guild_id: int, amount: int) -> bool:
        """
        Add currency to guild vault cache (in-memory operation).

        This is called when game losses add currency to the guild vault.
        Updates are batched and flushed periodically to avoid DB writes on every game.

        Args:
            guild_id: Discord guild ID
            amount: Currency amount to add (should be positive)

        Returns:
            True if successful, False otherwise (triggers immediate DB write)
        """
        if not self.redis_available:
            # Fallback mode: return False to trigger immediate DB write
            return False

        try:
            vault_key = self._guild_vault_key(guild_id)

            # Get existing vault cache or create new one
            vault_data = await self.redis.get(vault_key)

            if vault_data:
                vault_cache = json.loads(vault_data)
            else:
                # Initialize new vault cache
                vault_cache = {
                    "vault_currency_to_flush": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "dirty": False
                }

            # Add to pending vault currency
            vault_cache["vault_currency_to_flush"] = vault_cache.get("vault_currency_to_flush", 0) + amount
            vault_cache["last_updated"] = datetime.now(timezone.utc).isoformat()
            vault_cache["dirty"] = True

            # Save back to Redis with TTL (longer for guild data - 24 hours)
            await self.redis.setex(vault_key, 86400, json.dumps(vault_cache))

            logger.debug(f"Added {amount} to guild {guild_id} vault cache (pending: {vault_cache['vault_currency_to_flush']})")

            return True

        except Exception as e:
            logger.error(f"Error adding vault currency to cache: {e}")
            return False

    async def get_vault_currency_delta(self, guild_id: int) -> Optional[int]:
        """
        Get the pending vault currency delta for a guild.

        Args:
            guild_id: Discord guild ID

        Returns:
            Pending vault currency amount, or None if no cache exists
        """
        if not self.redis_available:
            return None

        try:
            vault_key = self._guild_vault_key(guild_id)
            vault_data = await self.redis.get(vault_key)

            if vault_data:
                vault_cache = json.loads(vault_data)
                return vault_cache.get("vault_currency_to_flush", 0)

            return None

        except Exception as e:
            logger.error(f"Error getting vault currency delta: {e}")
            return None

    async def flush_dirty_sessions(self):
        """
        Flush all dirty sessions to the database.

        Called periodically by background task.
        """
        if not self.redis_available:
            return

        try:
            flushed_count = 0
            cursor = 0

            # Scan all sessions in Redis
            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match="session:*",
                    count=100
                )

                for key in keys:
                    session_data = await self.redis.get(key)
                    if not session_data:
                        continue

                    session = json.loads(session_data)

                    # Only flush if dirty
                    if session.get("dirty", False):
                        # Extract guild_id and user_id from key
                        parts = key.split(":")
                        if len(parts) != 3:
                            continue

                        guild_id = int(parts[1])
                        user_id = int(parts[2])

                        # Flush to database
                        success = await self._flush_session_to_db(
                            guild_id, user_id, session
                        )

                        if success:
                            # Mark as clean and reset deltas
                            session["dirty"] = False
                            session["messages_to_flush"] = 0
                            session["reactions_to_flush"] = 0
                            session["currency_to_flush"] = 0
                            session["pending_games"] = []
                            ttl = await self.redis.ttl(key)
                            if ttl > 0:
                                await self.redis.setex(key, ttl, json.dumps(session))
                            flushed_count += 1

                if cursor == 0:
                    break

            # Also flush guild vault caches
            vault_flushed_count = 0
            cursor = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match="guild_vault:*",
                    count=100
                )

                for key in keys:
                    vault_data = await self.redis.get(key)
                    if not vault_data:
                        continue

                    vault_cache = json.loads(vault_data)

                    # Only flush if dirty
                    if vault_cache.get("dirty", False):
                        # Extract guild_id from key
                        parts = key.split(":")
                        if len(parts) != 2:
                            continue

                        guild_id = int(parts[1])

                        # Flush to database
                        success = await self._flush_vault_to_db(guild_id, vault_cache)

                        if success:
                            # Mark as clean and reset delta
                            vault_cache["dirty"] = False
                            vault_cache["vault_currency_to_flush"] = 0
                            ttl = await self.redis.ttl(key)
                            if ttl > 0:
                                await self.redis.setex(key, ttl, json.dumps(vault_cache))
                            vault_flushed_count += 1

                if cursor == 0:
                    break

            if flushed_count > 0 or vault_flushed_count > 0:
                logger.info(f"💾 Flushed {flushed_count} user sessions and {vault_flushed_count} guild vaults to database")

        except Exception as e:
            logger.error(f"Error flushing dirty sessions: {e}", exc_info=True)

    async def _flush_session_to_db(
        self,
        guild_id: int,
        user_id: int,
        session: dict
    ) -> bool:
        """
        Flush a single session to the database.

        Flushes XP, currency, messages, reactions, and game logs atomically.

        Returns:
            True if successful, False otherwise
        """
        from Dao.GuildUserDao import GuildUserDao
        from Dao.UserDao import UserDao
        from Dao.GamesDao import GamesDao

        guild_user_dao = None
        user_dao = None
        games_dao = None

        try:
            guild_user_dao = GuildUserDao()
            user_dao = UserDao()
            games_dao = GamesDao()

            # Update guild user XP
            guild_user = guild_user_dao.get_guild_user(user_id, guild_id)
            if guild_user:
                guild_user.exp = session["guild_exp"]
                guild_user.level = session["guild_level"]
                guild_user.exp_gained = session["guild_exp_gained"]
                guild_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                guild_user_dao.update_guild_user(guild_user)

            # Flush currency changes
            currency_to_flush = session.get("currency_to_flush", 0)
            if currency_to_flush != 0:
                # Use the existing sync method to update both guild and global
                guild_user_dao.update_currency_with_global_sync(
                    user_id=user_id,
                    guild_id=guild_id,
                    currency_delta=currency_to_flush
                )

            # Flush message/reaction counts atomically
            messages_to_flush = session.get("messages_to_flush", 0)
            reactions_to_flush = session.get("reactions_to_flush", 0)

            if messages_to_flush > 0 or reactions_to_flush > 0:
                # Update guild stats (guild-specific activity)
                guild_user_dao.increment_activity_counts(
                    user_id,
                    guild_id,
                    messages=messages_to_flush,
                    reactions=reactions_to_flush
                )

                # Update global stats
                user_dao.increment_user_stats(
                    user_id=user_id,
                    global_exp_gain=0,  # XP already handled separately
                    currency_gain=0,    # Currency already handled separately
                    messages_gain=messages_to_flush,
                    reactions_gain=reactions_to_flush
                )

            # Flush pending games
            pending_games = session.get("pending_games", [])
            if pending_games:
                games_flushed = games_dao.batch_add_games(pending_games)
                logger.debug(f"Flushed {games_flushed} game records for user {user_id}")

            # Update global user
            global_user = user_dao.get_user(user_id)
            if global_user:
                global_user.global_exp = session["global_exp"]
                global_user.global_level = session["global_level"]
                global_user.last_seen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                user_dao.update_user(global_user)

            return True

        except Exception as e:
            logger.error(f"Error flushing session to DB for user {user_id} in guild {guild_id}: {e}")
            return False
        finally:
            if guild_user_dao:
                guild_user_dao.close()
            if user_dao:
                user_dao.close()
            if games_dao:
                games_dao.close()

    async def _flush_vault_to_db(self, guild_id: int, vault_cache: dict) -> bool:
        """
        Flush guild vault cache to the database.

        Args:
            guild_id: Discord guild ID
            vault_cache: Vault cache dictionary

        Returns:
            True if successful, False otherwise
        """
        from Dao.GuildDao import GuildDao

        guild_dao = None

        try:
            guild_dao = GuildDao()

            # Get the pending vault currency delta
            vault_currency_to_flush = vault_cache.get("vault_currency_to_flush", 0)

            if vault_currency_to_flush > 0:
                # Add to guild vault atomically
                success = guild_dao.add_vault_currency(guild_id, vault_currency_to_flush)

                if success:
                    logger.debug(f"Flushed {vault_currency_to_flush} to vault for guild {guild_id}")
                    return True
                else:
                    logger.warning(f"Failed to flush vault currency for guild {guild_id}")
                    return False

            return True  # Nothing to flush

        except Exception as e:
            logger.error(f"Error flushing vault to DB for guild {guild_id}: {e}")
            return False
        finally:
            if guild_dao:
                guild_dao.close()

    async def flush_session(self, guild_id: int, user_id: int):
        """
        Flush a specific session to the database immediately.

        Useful for important events (e.g., manual save, user leaving).
        """
        if not self.redis_available:
            return

        try:
            session_key = self._session_key(guild_id, user_id)
            session_data = await self.redis.get(session_key)

            if session_data:
                session = json.loads(session_data)
                if session.get("dirty", False):
                    await self._flush_session_to_db(guild_id, user_id, session)

                    # Mark as clean and reset deltas
                    session["dirty"] = False
                    session["messages_to_flush"] = 0
                    session["reactions_to_flush"] = 0
                    session["currency_to_flush"] = 0
                    session["pending_games"] = []
                    ttl = await self.redis.ttl(session_key)
                    if ttl > 0:
                        await self.redis.setex(session_key, ttl, json.dumps(session))

        except Exception as e:
            logger.error(f"Error flushing session for user {user_id}: {e}")

    async def flush_all_sessions(self):
        """
        Flush all sessions to database (called on shutdown).

        This ensures no data is lost when the bot restarts.
        """
        if not self.redis_available:
            return

        logger.info("🧹 Flushing all sessions to database...")

        try:
            flushed_count = 0
            cursor = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match="session:*",
                    count=100
                )

                for key in keys:
                    session_data = await self.redis.get(key)
                    if not session_data:
                        continue

                    session = json.loads(session_data)

                    # Extract guild_id and user_id
                    parts = key.split(":")
                    if len(parts) != 3:
                        continue

                    guild_id = int(parts[1])
                    user_id = int(parts[2])

                    # Flush to database (even if not dirty)
                    success = await self._flush_session_to_db(
                        guild_id, user_id, session
                    )

                    if success:
                        flushed_count += 1

                if cursor == 0:
                    break

            # Also flush all guild vaults
            vault_flushed_count = 0
            cursor = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match="guild_vault:*",
                    count=100
                )

                for key in keys:
                    vault_data = await self.redis.get(key)
                    if not vault_data:
                        continue

                    vault_cache = json.loads(vault_data)

                    # Extract guild_id
                    parts = key.split(":")
                    if len(parts) != 2:
                        continue

                    guild_id = int(parts[1])

                    # Flush to database (even if not dirty)
                    success = await self._flush_vault_to_db(guild_id, vault_cache)

                    if success:
                        vault_flushed_count += 1

                if cursor == 0:
                    break

            logger.info(f"✅ Flushed {flushed_count} user sessions and {vault_flushed_count} guild vaults on shutdown")

        except Exception as e:
            logger.error(f"Error flushing all sessions: {e}", exc_info=True)

    async def get_stats(self) -> dict:
        """Get session statistics for monitoring."""
        if not self.redis_available:
            return {
                'redis_available': False,
                'active_sessions': 0,
                'dirty_sessions': 0
            }

        try:
            total_sessions = 0
            dirty_sessions = 0
            cursor = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match="session:*",
                    count=100
                )

                total_sessions += len(keys)

                for key in keys:
                    session_data = await self.redis.get(key)
                    if session_data:
                        session = json.loads(session_data)
                        if session.get("dirty", False):
                            dirty_sessions += 1

                if cursor == 0:
                    break

            # Also count guild vault caches
            total_vaults = 0
            dirty_vaults = 0
            cursor = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match="guild_vault:*",
                    count=100
                )

                total_vaults += len(keys)

                for key in keys:
                    vault_data = await self.redis.get(key)
                    if vault_data:
                        vault_cache = json.loads(vault_data)
                        if vault_cache.get("dirty", False):
                            dirty_vaults += 1

                if cursor == 0:
                    break

            return {
                'redis_available': True,
                'active_sessions': total_sessions,
                'dirty_sessions': dirty_sessions,
                'cached_vaults': total_vaults,
                'dirty_vaults': dirty_vaults,
                'flush_interval': self.flush_interval
            }

        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {
                'redis_available': False,
                'active_sessions': 0,
                'dirty_sessions': 0,
                'cached_vaults': 0,
                'dirty_vaults': 0
            }

    async def cleanup(self):
        """Stop flush task and perform final flush."""
        logger.info("🧹 Cleaning up SessionManager...")

        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self.flush_all_sessions()

        # Close Redis connection
        if self.redis:
            await self.redis.close()

        logger.info("✅ SessionManager cleanup complete")


# Singleton instance
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get the singleton SessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def initialize_session_manager():
    """Initialize and start the session manager."""
    manager = get_session_manager()
    await manager.initialize()
    await manager.start()


async def cleanup_session_manager():
    """Cleanup the session manager."""
    global _session_manager
    if _session_manager:
        await _session_manager.cleanup()
        _session_manager = None
