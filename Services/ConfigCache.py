"""
  Guild Configuration Cache with Redis Pub/Sub Invalidation

  This service provides a high-performance caching layer for guild settings.
  - Local in-memory cache for instant reads
  - Redis pub/sub for instant cache invalidation across all bot instances
  - Automatic fallback if Redis is unavailable
  """

from cachetools import TTLCache
import asyncio
import redis.asyncio as aioredis
import json
import os
from datetime import datetime
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class GuildConfigCache:
    """
    High-performance guild configuration cache with distributed invalidation.

    Features:
    - In-memory cache for sub-millisecond reads
    - Redis pub/sub for instant invalidation across shards
    - 300-second TTL as fallback if Redis fails
    - Thread-safe operations
    """

    def __init__(self):
        # Local in-memory cache (TTL as backup if Redis fails)
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5 min TTL as fallback
        self.lock = asyncio.Lock()

        # Redis connection for pub/sub
        self.redis = None
        self.pubsub = None
        self.listener_task = None
        self.redis_available = False

        # Default configuration
        self.default_config = {
            "enabled": True,
            "exp_per_message": 10,
            "exp_cooldown_seconds": 3,
            "level_up_announcements": False,  # Default to False to prevent spam if settings can't be fetched
            "announcement_channel_id": None,
            "streak_multiplier": 0.05,
            "max_streak_bonus": 20,
            "daily_bonus": 1000,
            "daily_announcements_enabled": False,
            "daily_announcement_channel_id": None,
            "level_up_message": "🎉 {mention} GUILD LEVEL UP! You have reached level {level}! Gained {credits} Credits!",
            "level_up_message_with_streak": "🎉 {mention} GUILD LEVEL UP! You have reached level {level}! Gained {credits} Credits! {base_credits} + {streak_bonus} from {streak}x Streak!"
        }

    async def initialize(self):
        """
        Initialize Redis connection and start listening for invalidation events.

        This should be called once during bot startup.
        If Redis is unavailable, the cache will still work with TTL fallback.
        """
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_password = os.getenv('REDIS_PASSWORD', None)

            logger.info(f"Connecting to Redis at {redis_url}...")

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

            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe('guild_config_invalidate')

            # Start background listener
            self.listener_task = asyncio.create_task(self._listen_for_invalidations())
            self.redis_available = True

            logger.info("✅ ConfigCache Redis listener initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis for ConfigCache: {e}")
            logger.warning("⚠️  ConfigCache will work with TTL fallback only (no instant invalidation)")
            self.redis_available = False

    async def _listen_for_invalidations(self):
        """
        Background task that listens for invalidation messages from Redis.

        When the API publishes a guild_id to 'guild_config_invalidate' channel,
        this listener removes that guild's config from the local cache.
        """
        logger.info("🎧 ConfigCache listener started")

        try:
            while True:
                try:
                    message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

                    if message and message['type'] == 'message':
                        try:
                            guild_id = int(message['data'])
                            async with self.lock:
                                removed = self.cache.pop(guild_id, None) is not None

                            if removed:
                                logger.info(f"⚡ Cache invalidated for guild {guild_id} via Redis pub/sub")
                            else:
                                logger.debug(f"🔄 Received invalidation for uncached guild {guild_id}")
                        except ValueError as e:
                            logger.error(f"Invalid guild_id in invalidation message: {message['data']}")
                        except Exception as e:
                            logger.error(f"Error processing invalidation message: {e}")

                    await asyncio.sleep(0.1)

                except Exception as e:
                    if not isinstance(e, asyncio.CancelledError):
                        logger.error(f"Error in listener loop: {e}")
                        await asyncio.sleep(1)  # Back off on error
                    else:
                        raise

        except asyncio.CancelledError:
            logger.info("🛑 ConfigCache listener stopped")
            raise
        except Exception as e:
            logger.error(f"Fatal error in ConfigCache listener: {e}")
            self.redis_available = False

    async def get_leveling_config(self, guild_id: int) -> dict:
        """
        Get leveling configuration for a guild.

        Priority:
        1. Check local cache (instant)
        2. If miss, fetch from database
        3. Store in cache for future requests

        Args:
            guild_id: Discord guild ID

        Returns:
            Dict containing leveling configuration with defaults applied
        """
        # Check cache first (fast path)
        async with self.lock:
            if guild_id in self.cache:
                logger.debug(f"📦 Cache HIT for guild {guild_id}")
                # Record cache hit
                try:
                    from Services.PerformanceMonitor import get_performance_monitor
                    perf_monitor = get_performance_monitor()
                    await perf_monitor.record_config_cache_hit()
                except:
                    pass  # Don't fail if monitor not available
                return self.cache[guild_id].copy()

        logger.debug(f"💾 Cache MISS for guild {guild_id}, fetching from DB")

        # Record cache miss
        try:
            from Services.PerformanceMonitor import get_performance_monitor
            perf_monitor = get_performance_monitor()
            await perf_monitor.record_config_cache_miss()
        except:
            pass  # Don't fail if monitor not available

        # Cache miss - fetch from DB
        from Dao.GuildDao import GuildDao

        guild_dao = GuildDao()
        try:
            guild = guild_dao.get_guild(guild_id)

            if not guild or not guild.settings:
                config = self.default_config.copy()
                logger.debug(f"Using default config for guild {guild_id}")
            else:
                settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings
                leveling_settings = settings.get("leveling", {})

                # Merge with defaults
                config = self.default_config.copy()
                config.update(leveling_settings)
                logger.debug(f"Loaded custom config for guild {guild_id}")

            # Store in cache
            async with self.lock:
                self.cache[guild_id] = config

            return config.copy()

        except Exception as e:
            logger.error(f"Error fetching config for guild {guild_id}: {e}")
            # Return default config on error
            return self.default_config.copy()
        finally:
            guild_dao.close()

    async def invalidate_local(self, guild_id: int):
        """
        Manually invalidate cache for a guild (local only, no Redis broadcast).

        Use this for testing or emergency cache clearing.
        """
        async with self.lock:
            removed = self.cache.pop(guild_id, None) is not None

        if removed:
            logger.info(f"🗑️  Manually invalidated cache for guild {guild_id}")
        return removed

    async def get_cache_stats(self) -> dict:
        """Get cache statistics for monitoring."""
        async with self.lock:
            return {
                "size": len(self.cache),
                "maxsize": self.cache.maxsize,
                "ttl": self.cache.ttl,
                "redis_available": self.redis_available,
                "cached_guilds": list(self.cache.keys())
            }

    async def cleanup(self):
        """
        Cleanup Redis connections gracefully.

        This should be called during bot shutdown.
        """
        logger.info("🧹 Cleaning up ConfigCache...")

        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            try:
                await self.pubsub.unsubscribe('guild_config_invalidate')
                await self.pubsub.close()
            except Exception as e:
                logger.error(f"Error closing pubsub: {e}")

        if self.redis:
            try:
                await self.redis.close()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

        logger.info("✅ ConfigCache cleanup complete")


# Singleton instance
_config_cache = None


def get_config_cache() -> GuildConfigCache:
    """Get the singleton ConfigCache instance."""
    global _config_cache
    if _config_cache is None:
        _config_cache = GuildConfigCache()
    return _config_cache


async def initialize_config_cache():
    """Initialize the config cache. Call this from bot startup."""
    cache = get_config_cache()
    await cache.initialize()


async def cleanup_config_cache():
    """Cleanup the config cache. Call this from bot shutdown."""
    global _config_cache
    if _config_cache:
        await _config_cache.cleanup()
        _config_cache = None
