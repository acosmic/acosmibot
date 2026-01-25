"""
XP Session Management Service

Treats each active user as having a temporary session in Redis.
XP and level calculations happen entirely in memory, with periodic
persistence to the database.

Session Lifecycle:
1. Session Start: First message loads user data from DB, creates Redis session
2. Active Session: All XP gains modify Redis only, level-ups detected instantly
3. Session Keepalive: Each activity extends TTL
4. Session End: Inactivity (60min) or manual flush persists to DB

Benefits:
- 99% reduction in XP-related database writes
- Instant level-up detection (no DB latency)
- Automatic cleanup of idle sessions
- Crash-safe with periodic flushes
"""

import asyncio
import json
import math
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict
import redis.asyncio as aioredis
import os
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class XPSessionManager:
    """
    Manages in-memory XP sessions for active users.

    Each session contains:
    - Current XP and level
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

        logger.info("XPSessionManager initialized")

    async def initialize(self):
        """
        Initialize Redis connection and start background flush task.

        If Redis is unavailable, falls back to in-memory sessions with
        immediate DB writes (same as current behavior).
        """
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_password = os.getenv('REDIS_PASSWORD', None)

            logger.info(f"XPSessionManager connecting to Redis at {redis_url}...")

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
            logger.info("✅ XPSessionManager connected to Redis successfully")

        except Exception as e:
            logger.warning(f"⚠️ XPSessionManager could not connect to Redis: {e}")
            logger.warning("⚠️ Falling back to immediate DB writes (no session caching)")
            self.redis_available = False

    async def start(self):
        """Start the periodic flush task."""
        if self.redis_available:
            self.flush_task = asyncio.create_task(self._periodic_flush())
            logger.info(f"🎮 XP session management started (flushes every {self.flush_interval}s)")
        else:
            logger.info("🎮 XP session management in fallback mode (no Redis)")

    async def _periodic_flush(self):
        """Background task that periodically flushes dirty sessions."""
        try:
            while True:
                await asyncio.sleep(self.flush_interval)
                await self.flush_dirty_sessions()
        except asyncio.CancelledError:
            logger.info("XP session flush task stopped")
            raise

    def _session_key(self, guild_id: int, user_id: int) -> str:
        """Generate Redis key for user session."""
        return f"xp_session:{guild_id}:{user_id}"

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

                # Session metadata
                "last_active": datetime.now(timezone.utc).isoformat(),
                "last_xp_gain": None,  # No XP gained yet this session
                "session_start": datetime.now(timezone.utc).isoformat(),
                "dirty": False,  # No changes yet
                "messages_this_session": 0,

                # Activity tracking (NEW)
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

            logger.info(f"🎮 Created XP session for user {user_id} in guild {guild_id} (Level {session['guild_level']}, {session['guild_exp']} XP)")

            return session

        except Exception as e:
            logger.error(f"Error getting/creating XP session: {e}", exc_info=True)
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

            # Scan all XP sessions in Redis
            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match="xp_session:*",
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
                            ttl = await self.redis.ttl(key)
                            if ttl > 0:
                                await self.redis.setex(key, ttl, json.dumps(session))
                            flushed_count += 1

                if cursor == 0:
                    break

            if flushed_count > 0:
                logger.info(f"💾 Flushed {flushed_count} dirty XP sessions to database")

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

        Returns:
            True if successful, False otherwise
        """
        from Dao.GuildUserDao import GuildUserDao
        from Dao.UserDao import UserDao

        guild_user_dao = None
        user_dao = None

        try:
            guild_user_dao = GuildUserDao()
            user_dao = UserDao()

            # Update guild user
            guild_user = guild_user_dao.get_guild_user(user_id, guild_id)
            if guild_user:
                guild_user.exp = session["guild_exp"]
                guild_user.level = session["guild_level"]
                guild_user.exp_gained = session["guild_exp_gained"]
                guild_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                guild_user_dao.update_guild_user(guild_user)

            # Flush message/reaction counts atomically
            messages_to_flush = session.get("messages_to_flush", 0)
            reactions_to_flush = session.get("reactions_to_flush", 0)

            if messages_to_flush > 0 or reactions_to_flush > 0:
                # 1. Update guild stats (guild-specific activity)
                guild_user_dao.increment_activity_counts(
                    user_id,
                    guild_id,
                    messages=messages_to_flush,
                    reactions=reactions_to_flush
                )

                # 2. Update global stats (NEW - fixes asymmetric message/reaction handling)
                user_dao.increment_user_stats(
                    user_id=user_id,
                    global_exp_gain=0,  # XP already handled separately
                    currency_gain=0,
                    messages_gain=messages_to_flush,
                    reactions_gain=reactions_to_flush
                )

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

        logger.info("🧹 Flushing all XP sessions to database...")

        try:
            flushed_count = 0
            cursor = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match="xp_session:*",
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

            logger.info(f"✅ Flushed {flushed_count} XP sessions on shutdown")

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
                    match="xp_session:*",
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

            return {
                'redis_available': True,
                'active_sessions': total_sessions,
                'dirty_sessions': dirty_sessions,
                'flush_interval': self.flush_interval
            }

        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {
                'redis_available': False,
                'active_sessions': 0,
                'dirty_sessions': 0
            }

    async def cleanup(self):
        """Stop flush task and perform final flush."""
        logger.info("🧹 Cleaning up XPSessionManager...")

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

        logger.info("✅ XPSessionManager cleanup complete")


# Singleton instance
_xp_session_manager = None


def get_xp_session_manager() -> XPSessionManager:
    """Get the singleton XPSessionManager instance."""
    global _xp_session_manager
    if _xp_session_manager is None:
        _xp_session_manager = XPSessionManager()
    return _xp_session_manager


async def initialize_xp_session_manager():
    """Initialize and start the XP session manager."""
    manager = get_xp_session_manager()
    await manager.initialize()
    await manager.start()


async def cleanup_xp_session_manager():
    """Cleanup the XP session manager."""
    global _xp_session_manager
    if _xp_session_manager:
        await _xp_session_manager.cleanup()
        _xp_session_manager = None
