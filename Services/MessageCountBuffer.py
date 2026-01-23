"""
Message Count Buffering Service

Buffers non-critical stats (message counts, last active) in memory and flushes
periodically to reduce database writes while keeping XP/level-up system immediate.

Key Design:
- Message counts updated in memory on every message (instant for user)
- Flushed to database every 30 seconds (or on bot shutdown)
- XP system remains immediate (separate path)
- Acceptable data loss: up to 30 seconds of message counts on crash
"""

import asyncio
from datetime import datetime
from typing import Dict, Tuple
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class MessageCountBuffer:
    """
    In-memory buffer for message counts and activity timestamps.

    Reduces database writes by batching non-critical stats updates.
    XP gains are NOT buffered - they go directly to DB for level detection.
    """

    def __init__(self):
        # Buffer: (guild_id, user_id) -> {'messages': int, 'last_active': datetime}
        self.buffer: Dict[Tuple[int, int], Dict] = {}
        self.lock = asyncio.Lock()

        # Flush settings
        self.flush_interval = 30  # Flush every 30 seconds
        self.flush_task = None

        logger.info("MessageCountBuffer initialized")

    async def start(self):
        """Start the periodic flush task."""
        self.flush_task = asyncio.create_task(self._periodic_flush())
        logger.info(f"📊 Message count buffering started (flushes every {self.flush_interval}s)")

    async def _periodic_flush(self):
        """Background task that periodically flushes the buffer."""
        try:
            while True:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
        except asyncio.CancelledError:
            logger.info("Message count buffer flush task stopped")
            raise

    async def increment_activity(self, guild_id: int, user_id: int):
        """
        Increment message count and update last active for a user.

        This is called on EVERY message but only updates in-memory buffer.
        The buffer is flushed to DB periodically.

        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
        """
        async with self.lock:
            key = (guild_id, user_id)

            if key not in self.buffer:
                self.buffer[key] = {
                    'messages': 0,
                    'last_active': None
                }

            self.buffer[key]['messages'] += 1
            self.buffer[key]['last_active'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def flush(self):
        """
        Flush buffered message counts to the database.

        Uses bulk update for efficiency. Called periodically by background task
        or manually during shutdown.
        """
        async with self.lock:
            if not self.buffer:
                return  # Nothing to flush

            # Take snapshot and clear buffer
            to_flush = dict(self.buffer)
            self.buffer.clear()

        # Flush outside the lock to avoid blocking
        try:
            from Dao.GuildUserDao import GuildUserDao

            guild_user_dao = GuildUserDao()
            try:
                # Prepare updates
                updates = []
                for (guild_id, user_id), data in to_flush.items():
                    updates.append({
                        'user_id': user_id,
                        'guild_id': guild_id,
                        'messages': data['messages'],
                        'last_active': data['last_active']
                    })

                # Bulk update
                success = await self._bulk_increment_activity(guild_user_dao, updates)

                if success:
                    logger.info(f"💾 Flushed {len(updates)} message count updates to database")
                else:
                    logger.warning(f"⚠️ Failed to flush message counts, will retry next cycle")
                    # Re-add to buffer for retry
                    async with self.lock:
                        for (guild_id, user_id), data in to_flush.items():
                            key = (guild_id, user_id)
                            if key in self.buffer:
                                # Merge with any new updates
                                self.buffer[key]['messages'] += data['messages']
                                self.buffer[key]['last_active'] = data['last_active']
                            else:
                                self.buffer[key] = data
            finally:
                guild_user_dao.close()

        except Exception as e:
            logger.error(f"Error flushing message counts: {e}")
            # Don't crash the bot, just log and continue

    async def _bulk_increment_activity(self, guild_user_dao, updates) -> bool:
        """
        Execute bulk update for message counts and last active.

        Uses ON DUPLICATE KEY UPDATE to atomically increment message counts.
        """
        if not updates:
            return True

        sql = """
            INSERT INTO GuildUsers (user_id, guild_id, messages_sent, last_active)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                messages_sent = messages_sent + VALUES(messages_sent),
                last_active = VALUES(last_active)
        """

        values_list = [
            (u['user_id'], u['guild_id'], u['messages'], u['last_active'])
            for u in updates
        ]

        try:
            # Use execute_many for bulk insert
            guild_user_dao.execute_many(sql, values_list, commit=True)
            return True
        except Exception as e:
            logger.error(f"Error in bulk activity update: {e}")
            return False

    async def get_stats(self) -> dict:
        """Get buffer statistics."""
        async with self.lock:
            total_messages = sum(data['messages'] for data in self.buffer.values())
            return {
                'buffered_users': len(self.buffer),
                'buffered_messages': total_messages,
                'flush_interval': self.flush_interval
            }

    async def cleanup(self):
        """Stop the flush task and perform final flush."""
        logger.info("🧹 Cleaning up MessageCountBuffer...")

        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self.flush()

        logger.info("✅ MessageCountBuffer cleanup complete")


# Singleton instance
_message_count_buffer = None


def get_message_count_buffer() -> MessageCountBuffer:
    """Get the singleton MessageCountBuffer instance."""
    global _message_count_buffer
    if _message_count_buffer is None:
        _message_count_buffer = MessageCountBuffer()
    return _message_count_buffer


async def initialize_message_count_buffer():
    """Initialize and start the message count buffer."""
    buffer = get_message_count_buffer()
    await buffer.start()


async def cleanup_message_count_buffer():
    """Cleanup the message count buffer."""
    global _message_count_buffer
    if _message_count_buffer:
        await _message_count_buffer.cleanup()
        _message_count_buffer = None
