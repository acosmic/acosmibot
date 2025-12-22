from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

import logging
logger = logging.getLogger(__name__)

class YoutubeDao:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_youtube_subscription(self, guild_id: int, channel_id: str, channel_name: Optional[str] = None) -> None:
        """
        Adds a guild to a YouTube channel's tracked_guild_ids array.
        Creates the channel record if it doesn't exist.
        Uses the Twitch pattern: ONE row per channel with JSON array of guild IDs.
        """
        # First, check if channel record exists
        check_query = text("""
            SELECT tracked_guild_ids, guild_count
            FROM YouTubeSubscriptions
            WHERE channel_id = :channel_id
        """)
        result = await self.session.execute(check_query, {"channel_id": channel_id})
        existing = result.fetchone()

        if existing:
            # Channel record exists - add guild to array if not already present
            tracked_guilds = existing[0] or []
            guild_id_str = str(guild_id)

            if guild_id_str not in tracked_guilds:
                # Add guild to tracked_guild_ids array
                update_query = text("""
                    UPDATE YouTubeSubscriptions
                    SET tracked_guild_ids = JSON_ARRAY_APPEND(
                            COALESCE(tracked_guild_ids, JSON_ARRAY()),
                            '$',
                            :guild_id
                        ),
                        guild_count = guild_count + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE channel_id = :channel_id
                """)
                await self.session.execute(update_query, {
                    "channel_id": channel_id,
                    "guild_id": guild_id_str
                })
                logger.info(f"Added guild {guild_id} to YouTube channel {channel_id}")
            else:
                logger.info(f"Guild {guild_id} already subscribed to YouTube channel {channel_id}")
        else:
            # Channel record doesn't exist - create new record
            insert_query = text("""
                INSERT INTO YouTubeSubscriptions (
                    channel_id, channel_name, tracked_guild_ids, guild_count
                )
                VALUES (
                    :channel_id,
                    :channel_name,
                    JSON_ARRAY(:guild_id),
                    1
                )
            """)
            await self.session.execute(insert_query, {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "guild_id": str(guild_id)
            })
            logger.info(f"Created YouTube channel record {channel_id} with guild {guild_id}")

        await self.session.commit()

    async def remove_youtube_subscription(self, guild_id: int, channel_id: str) -> bool:
        """
        Removes a guild from a YouTube channel's tracked_guild_ids array.
        Returns True if the guild was successfully removed.
        """
        guild_id_str = str(guild_id)

        # Remove guild from tracked_guild_ids array using JSON_REMOVE
        query = text("""
            UPDATE YouTubeSubscriptions
            SET tracked_guild_ids = JSON_REMOVE(
                    tracked_guild_ids,
                    REPLACE(JSON_UNQUOTE(JSON_SEARCH(tracked_guild_ids, 'one', :guild_id)), '"', '')
                ),
                guild_count = GREATEST(guild_count - 1, 0),
                updated_at = CURRENT_TIMESTAMP
            WHERE channel_id = :channel_id
              AND JSON_CONTAINS(tracked_guild_ids, JSON_QUOTE(:guild_id))
        """)

        result = await self.session.execute(query, {
            "channel_id": channel_id,
            "guild_id": guild_id_str
        })
        await self.session.commit()

        removed = result.rowcount > 0
        if removed:
            logger.info(f"Removed guild {guild_id} from YouTube channel {channel_id}")
        else:
            logger.warning(f"Guild {guild_id} was not subscribed to YouTube channel {channel_id}")

        return removed

    async def get_youtube_subscription_by_guild_and_channel(self, guild_id: int, channel_id: str) -> Optional[Tuple[int, str, Optional[str]]]:
        """
        Checks if a guild is subscribed to a YouTube channel.
        Returns (guild_id, channel_id, channel_name) if subscribed, None otherwise.
        """
        guild_id_str = str(guild_id)

        query = text("""
            SELECT :guild_id_int as guild_id, channel_id, channel_name
            FROM YouTubeSubscriptions
            WHERE channel_id = :channel_id
              AND JSON_CONTAINS(tracked_guild_ids, JSON_QUOTE(:guild_id_str))
        """)
        result = await self.session.execute(query, {
            "guild_id_int": guild_id,
            "channel_id": channel_id,
            "guild_id_str": guild_id_str
        })
        return result.fetchone()

    async def count_subscriptions_for_channel(self, channel_id: str) -> int:
        """
        Returns the number of guilds tracking a given YouTube channel.
        Now simply returns the guild_count field (optimized).
        """
        query = text("""
            SELECT guild_count
            FROM YouTubeSubscriptions
            WHERE channel_id = :channel_id
        """)
        result = await self.session.execute(query, {"channel_id": channel_id})
        row = result.fetchone()
        return row[0] if row else 0

    async def get_all_youtube_subscriptions(self) -> List[Tuple[int, str, Optional[str]]]:
        """
        Retrieves all active YouTube channel subscriptions (guild_id, channel_id, channel_name).
        Expands JSON array to return one row per guild-channel pair for backward compatibility.
        """
        query = text("""
            SELECT
                CAST(guild_id_json AS UNSIGNED) as guild_id,
                channel_id,
                channel_name
            FROM YouTubeSubscriptions
            CROSS JOIN JSON_TABLE(
                tracked_guild_ids,
                '$[*]' COLUMNS (guild_id_json VARCHAR(50) PATH '$')
            ) AS guilds
            WHERE guild_count > 0
        """)
        result = await self.session.execute(query)
        return result.fetchall()

    async def add_youtube_webhook_event(self, event_id: str, channel_id: str, video_id: str, event_type: str, payload: dict) -> None:
        """Adds a new YouTube webhook event."""
        query = text("""
            INSERT INTO YouTubeWebhookEvents (event_id, channel_id, video_id, event_type, payload)
            VALUES (:event_id, :channel_id, :video_id, :event_type, :payload)
        """)
        await self.session.execute(query, {
            "event_id": event_id,
            "channel_id": channel_id,
            "video_id": video_id,
            "event_type": event_type,
            "payload": json.dumps(payload)
        })
        await self.session.commit()

    async def get_unprocessed_webhook_events(self) -> List[Tuple[int, str, str, str, str, dict]]:
        """Retrieves unprocessed YouTube webhook events."""
        query = text("""
            SELECT id, event_id, channel_id, video_id, event_type, payload
            FROM YouTubeWebhookEvents
            WHERE processed_at IS NULL
            ORDER BY received_at ASC
        """)
        result = await self.session.execute(query)
        rows = result.fetchall()
        # Deserialize JSON payload back to dict
        return [(row[0], row[1], row[2], row[3], row[4], json.loads(row[5])) for row in rows]

    async def mark_webhook_event_as_processed(self, event_id: int) -> None:
        """Marks a YouTube webhook event as processed."""
        query = text("""
            UPDATE YouTubeWebhookEvents
            SET processed_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """)
        await self.session.execute(query, {"id": event_id})
        await self.session.commit()

    async def get_all_unique_subscribed_channels(self) -> List[str]:
        """Retrieves all unique YouTube channel IDs that have active subscriptions."""
        query = text("""
            SELECT DISTINCT channel_id
            FROM YouTubeSubscriptions
            ORDER BY channel_id
        """)
        result = await self.session.execute(query)
        return [row[0] for row in result.fetchall()]

    async def get_guilds_subscribed_to_channel(self, channel_id: str) -> List[Tuple[int, str]]:
        """
        Retrieves all guild IDs subscribed to a specific YouTube channel.
        Extracts from the tracked_guild_ids JSON array.

        Args:
            channel_id: YouTube channel ID

        Returns:
            List of tuples (guild_id, channel_name)
        """
        query = text("""
            SELECT
                CAST(guild_id_json AS UNSIGNED) as guild_id,
                channel_name
            FROM YouTubeSubscriptions
            CROSS JOIN JSON_TABLE(
                tracked_guild_ids,
                '$[*]' COLUMNS (guild_id_json VARCHAR(50) PATH '$')
            ) AS guilds
            WHERE channel_id = :channel_id
              AND guild_count > 0
            ORDER BY guild_id
        """)
        result = await self.session.execute(query, {"channel_id": channel_id})
        return result.fetchall()

    async def get_youtube_poll_tracking(self, channel_id: str) -> Optional[dict]:
        """Retrieves the poll tracking state for a YouTube channel."""
        query = text("""
            SELECT channel_id, last_video_id, last_published_at, last_poll_at
            FROM YouTubePollTracking
            WHERE channel_id = :channel_id
        """)
        result = await self.session.execute(query, {"channel_id": channel_id})
        row = result.fetchone()
        if row:
            return {
                "channel_id": row[0],
                "last_video_id": row[1],
                "last_published_at": row[2],
                "last_poll_at": row[3]
            }
        return None

    async def update_youtube_poll_tracking(self, channel_id: str, last_video_id: Optional[str], last_published_at: Optional[str]) -> None:
        """Updates or inserts the poll tracking state for a YouTube channel."""
        query = text("""
            INSERT INTO YouTubePollTracking (channel_id, last_video_id, last_published_at, last_poll_at)
            VALUES (:channel_id, :last_video_id, :last_published_at, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
                last_video_id = :last_video_id,
                last_published_at = :last_published_at,
                last_poll_at = CURRENT_TIMESTAMP
        """)
        await self.session.execute(query, {
            "channel_id": channel_id,
            "last_video_id": last_video_id,
            "last_published_at": last_published_at
        })
        await self.session.commit()
