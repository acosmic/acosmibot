#! /usr/bin/python3.10
"""
Data Access Object for StreamingAnnouncements table
Platform-agnostic DAO supporting both Twitch and YouTube streaming
"""
from Dao.BaseDao import BaseDao
from Entities.StreamingAnnouncement import StreamingAnnouncement
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StreamingAnnouncementDao(BaseDao):
    """
    DAO for managing streaming announcements across multiple platforms.
    Supports Twitch and YouTube with unified database operations.
    """

    def __init__(self):
        super().__init__(
            entity_class=StreamingAnnouncement,
            table_name='StreamingAnnouncements'
        )

    def create_announcement(
        self,
        platform: str,
        guild_id: int,
        channel_id: int,
        message_id: int,
        streamer_username: str,
        streamer_id: Optional[str],
        stream_id: Optional[str],
        stream_title: Optional[str],
        game_name: Optional[str],
        stream_started_at: datetime,
        initial_viewer_count: Optional[int] = None
    ) -> Optional[int]:
        """
        Create new streaming announcement record.

        Args:
            platform: 'twitch' or 'youtube'
            guild_id: Discord guild ID
            channel_id: Discord channel ID where announcement posted
            message_id: Discord message ID
            streamer_username: Platform username (@handle for YouTube)
            streamer_id: Platform user ID (Twitch user_id or YouTube channel_id)
            stream_id: Platform stream ID (Twitch stream_id or YouTube video_id)
            stream_title: Stream title
            game_name: Game/category name
            stream_started_at: Stream start timestamp
            initial_viewer_count: Viewer count at detection

        Returns:
            Inserted record ID or None on failure
        """
        query = """
            INSERT INTO StreamingAnnouncements (
                platform, guild_id, channel_id, message_id,
                streamer_username, streamer_id, stream_id,
                stream_title, game_name, stream_started_at,
                initial_viewer_count, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
        """
        params = (
            platform,
            guild_id,
            channel_id,
            message_id,
            streamer_username,
            streamer_id,
            stream_id,
            stream_title,
            game_name,
            stream_started_at,
            initial_viewer_count
        )

        try:
            cursor = self.execute_query(query, params)
            if cursor:
                announcement_id = cursor.lastrowid
                logger.info(
                    f"Created {platform} announcement {announcement_id} for "
                    f"{streamer_username} in guild {guild_id}"
                )
                return announcement_id
            return None
        except Exception as e:
            logger.error(f"Failed to create announcement: {e}")
            return None

    def mark_stream_offline(
        self,
        platform: str,
        guild_id: int,
        streamer_username: str,
        stream_ended_at: datetime
    ) -> bool:
        """
        Mark stream as ended and calculate duration.

        Args:
            platform: 'twitch' or 'youtube'
            guild_id: Discord guild ID
            streamer_username: Platform username
            stream_ended_at: Stream end timestamp

        Returns:
            True if updated successfully
        """
        query = """
            UPDATE StreamingAnnouncements
            SET
                stream_ended_at = %s,
                stream_duration_seconds = TIMESTAMPDIFF(SECOND, stream_started_at, %s),
                updated_at = NOW()
            WHERE platform = %s
              AND guild_id = %s
              AND streamer_username = %s
              AND stream_ended_at IS NULL
            ORDER BY stream_started_at DESC
            LIMIT 1
        """
        params = (
            stream_ended_at,
            stream_ended_at,
            platform,
            guild_id,
            streamer_username
        )

        try:
            cursor = self.execute_query(query, params)
            if cursor and cursor.rowcount > 0:
                logger.info(
                    f"Marked {platform} stream offline for {streamer_username} "
                    f"in guild {guild_id}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to mark stream offline: {e}")
            return False

    def get_announcements_needing_vod_check(
            self,
            platform: str,
            hours_threshold: int = 48,  # Increased threshold for longer-running VOD checks
            limit: int = 200  # Limit batch size for efficiency
    ) -> List[StreamingAnnouncement]:
        """
        Get announcements needing VOD check using exponential backoff logic.

        The time to the next check is calculated as:
        5 minutes * (2 ^ MIN(vod_check_attempts, 8))
        (Max backoff interval is ~21 hours, stopping after 10 attempts)
        """
        # The MAX_ATTEMPTS will be handled by the threshold in the WHERE clause (e.g., < 10)

        # NOTE: Using POWER(2, LEAST(vod_check_attempts, 8)) for exponential backoff.
        # This replaces the complex nested date logic with a single formula.
        query = """
                SELECT id, platform, guild_id, channel_id, message_id,
                       streamer_username, streamer_id, stream_id, stream_title, game_name,
                       stream_started_at, stream_ended_at, initial_viewer_count, final_viewer_count,
                       stream_duration_seconds, last_status_check_at, vod_url, vod_checked_at,
                       vod_check_attempts, created_at, updated_at
                FROM StreamingAnnouncements
                WHERE platform = %s
                  AND stream_ended_at IS NOT NULL
                  AND vod_url IS NULL
                  AND stream_ended_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                  AND vod_check_attempts < 4 -- Stop checking after 4 attempts
                  AND (
                    vod_checked_at IS NULL -- Should only happen if stream ended, but good safeguard
                        OR vod_checked_at <= DATE_SUB(
                            NOW(),
                            INTERVAL 5 * POWER(2, LEAST(vod_check_attempts, 8)) MINUTE
                  )
                    )
                ORDER BY vod_checked_at ASC, stream_ended_at ASC
                    LIMIT %s \
                """
        params = (platform, hours_threshold, limit)

        try:
            # ... (Execution logic remains the same, but using the new query/params)
            results = self.execute_query(query, params)
            if not results:
                return []

            # (Loop for populating the StreamingAnnouncement list)
            announcements = []
            for row in results:
                announcements.append(self.entity_class(*row))  # Assumes BaseDao/Entity supports unpacking

            logger.debug(
                f"Found {len(announcements)} {platform} announcements "
                f"needing VOD check based on backoff logic"
            )
            return announcements
        except Exception as e:
            logger.error(f"Failed to fetch announcements needing VOD check: {e}")
            return []

    def get_active_announcements_for_cache(
        self,
        platform: str
    ) -> List[StreamingAnnouncement]:
        """
        Get all active (not ended) announcements for cache initialization.

        Args:
            platform: 'twitch' or 'youtube'

        Returns:
            List of active announcements
        """
        query = """
            SELECT id, platform, guild_id, channel_id, message_id,
                   streamer_username, streamer_id, stream_id, stream_title, game_name,
                   stream_started_at, stream_ended_at, initial_viewer_count, final_viewer_count,
                   stream_duration_seconds, last_status_check_at, vod_url, vod_checked_at,
                   vod_check_attempts, created_at, updated_at
            FROM StreamingAnnouncements
            WHERE platform = %s
              AND stream_ended_at IS NULL
            ORDER BY stream_started_at DESC
        """
        params = (platform,)

        try:
            results = self.execute_query(query, params)
            if not results:
                return []

            announcements = []
            for row in results:
                announcement = StreamingAnnouncement(
                    id=row[0],
                    platform=row[1],
                    guild_id=row[2],
                    channel_id=row[3],
                    message_id=row[4],
                    streamer_username=row[5],
                    streamer_id=row[6],
                    stream_id=row[7],
                    stream_title=row[8],
                    game_name=row[9],
                    stream_started_at=row[10],
                    stream_ended_at=row[11],
                    initial_viewer_count=row[12],
                    final_viewer_count=row[13],
                    stream_duration_seconds=row[14],
                    last_status_check_at=row[15],
                    vod_url=row[16],
                    vod_checked_at=row[17],
                    vod_check_attempts=row[18],
                    created_at=row[19],
                    updated_at=row[20]
                )
                announcements.append(announcement)

            logger.info(
                f"Loaded {len(announcements)} active {platform} announcements "
                f"for cache"
            )
            return announcements
        except Exception as e:
            logger.error(f"Failed to fetch active announcements: {e}")
            return []

    def update_vod_info(
        self,
        announcement_id: int,
        vod_url: str
    ) -> bool:
        """
        Update announcement with VOD URL and mark as checked.
        """
        query = """
            UPDATE StreamingAnnouncements
            SET
                vod_url = %s,
                vod_checked_at = NOW(),
                vod_check_attempts = 0, -- Reset attempts (optional, but clean)
                updated_at = NOW()
            WHERE id = %s
        """
        # ... (execution logic remains the same)
        params = (vod_url, announcement_id)

        try:
            cursor = self.execute_query(query, params)
            if cursor and cursor.rowcount > 0:
                logger.info(f"Updated VOD info for announcement {announcement_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update VOD info: {e}")
            return False

    def mark_vod_checked(
        self,
        announcement_id: int
    ) -> bool:
        """
        Increment VOD check attempts counter (no VOD found).

        Args:
            announcement_id: Announcement ID

        Returns:
            True if updated successfully
        """
        query = """
            UPDATE StreamingAnnouncements
            SET
                vod_check_attempts = vod_check_attempts + 1,
                vod_checked_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """
        params = (announcement_id,)

        try:
            cursor = self.execute_query(query, params)
            if cursor and cursor.rowcount > 0:
                logger.debug(
                    f"Incremented VOD check attempts for announcement {announcement_id}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to mark VOD checked: {e}")
            return False

    def get_announcement_by_message(
        self,
        guild_id: int,
        message_id: int
    ) -> Optional[StreamingAnnouncement]:
        """
        Get announcement by Discord message ID.

        Args:
            guild_id: Discord guild ID
            message_id: Discord message ID

        Returns:
            StreamingAnnouncement or None
        """
        query = """
            SELECT id, platform, guild_id, channel_id, message_id,
                   streamer_username, streamer_id, stream_id, stream_title, game_name,
                   stream_started_at, stream_ended_at, initial_viewer_count, final_viewer_count,
                   stream_duration_seconds, last_status_check_at, vod_url, vod_checked_at,
                   vod_check_attempts, created_at, updated_at
            FROM StreamingAnnouncements
            WHERE guild_id = %s
              AND message_id = %s
            LIMIT 1
        """
        params = (guild_id, message_id)

        try:
            results = self.execute_query(query, params)
            if results and len(results) > 0:
                row = results[0]
                return StreamingAnnouncement(
                    id=row[0],
                    platform=row[1],
                    guild_id=row[2],
                    channel_id=row[3],
                    message_id=row[4],
                    streamer_username=row[5],
                    streamer_id=row[6],
                    stream_id=row[7],
                    stream_title=row[8],
                    game_name=row[9],
                    stream_started_at=row[10],
                    stream_ended_at=row[11],
                    initial_viewer_count=row[12],
                    final_viewer_count=row[13],
                    stream_duration_seconds=row[14],
                    last_status_check_at=row[15],
                    vod_url=row[16],
                    vod_checked_at=row[17],
                    vod_check_attempts=row[18],
                    created_at=row[19],
                    updated_at=row[20]
                )
            return None
        except Exception as e:
            logger.error(f"Failed to fetch announcement by message: {e}")
            return None

    def cleanup_old_announcements(
        self,
        days_threshold: int = 90
    ) -> int:
        """
        Delete announcements older than threshold (all platforms).

        Args:
            days_threshold: Delete announcements older than this many days

        Returns:
            Number of deleted records
        """
        query = """
            DELETE FROM StreamingAnnouncements
            WHERE stream_ended_at IS NOT NULL
              AND stream_ended_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        params = (days_threshold,)

        try:
            cursor = self.execute_query(query, params)
            if cursor:
                deleted_count = cursor.rowcount
                logger.info(
                    f"Cleaned up {deleted_count} announcements older than "
                    f"{days_threshold} days"
                )
                return deleted_count
            return 0
        except Exception as e:
            logger.error(f"Failed to cleanup old announcements: {e}")
            return 0

    def get_announcements_needing_status_update(
        self,
        platform: str,
        update_interval_minutes: int = 20
    ) -> List[StreamingAnnouncement]:
        """
        Get active streams needing status update (viewer count refresh).

        Args:
            platform: 'twitch' or 'youtube'
            update_interval_minutes: Update interval in minutes (default 20)

        Returns:
            List of announcements needing update
        """
        query = """
            SELECT id, platform, guild_id, channel_id, message_id,
                   streamer_username, streamer_id, stream_id, stream_title, game_name,
                   stream_started_at, stream_ended_at, initial_viewer_count, final_viewer_count,
                   stream_duration_seconds, last_status_check_at, vod_url, vod_checked_at,
                   vod_check_attempts, created_at, updated_at
            FROM StreamingAnnouncements
            WHERE platform = %s
              AND stream_ended_at IS NULL
              AND (
                  last_status_check_at IS NULL
                  OR last_status_check_at <= DATE_SUB(NOW(), INTERVAL %s MINUTE)
              )
            ORDER BY stream_started_at DESC
        """
        params = (platform, update_interval_minutes)

        try:
            results = self.execute_query(query, params)
            if not results:
                return []

            announcements = []
            for row in results:
                announcement = StreamingAnnouncement(
                    id=row[0],
                    platform=row[1],
                    guild_id=row[2],
                    channel_id=row[3],
                    message_id=row[4],
                    streamer_username=row[5],
                    streamer_id=row[6],
                    stream_id=row[7],
                    stream_title=row[8],
                    game_name=row[9],
                    stream_started_at=row[10],
                    stream_ended_at=row[11],
                    initial_viewer_count=row[12],
                    final_viewer_count=row[13],
                    stream_duration_seconds=row[14],
                    last_status_check_at=row[15],
                    vod_url=row[16],
                    vod_checked_at=row[17],
                    vod_check_attempts=row[18],
                    created_at=row[19],
                    updated_at=row[20]
                )
                announcements.append(announcement)

            logger.debug(
                f"Found {len(announcements)} {platform} announcements "
                f"needing status update"
            )
            return announcements
        except Exception as e:
            logger.error(f"Failed to fetch announcements needing status update: {e}")
            return []

    def update_last_status_check(
        self,
        announcement_id: int,
        current_viewer_count: Optional[int] = None
    ) -> bool:
        """
        Update last status check timestamp and optionally viewer count.

        Args:
            announcement_id: Announcement ID
            current_viewer_count: Current viewer count (optional)

        Returns:
            True if updated successfully
        """
        if current_viewer_count is not None:
            query = """
                UPDATE StreamingAnnouncements
                SET
                    last_status_check_at = NOW(),
                    final_viewer_count = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            params = (current_viewer_count, announcement_id)
        else:
            query = """
                UPDATE StreamingAnnouncements
                SET
                    last_status_check_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """
            params = (announcement_id,)

        try:
            cursor = self.execute_query(query, params)
            if cursor and cursor.rowcount > 0:
                logger.debug(
                    f"Updated status check timestamp for announcement {announcement_id}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update status check: {e}")
            return False

    def get_announcement_by_id(
        self,
        announcement_id: int
    ) -> Optional[StreamingAnnouncement]:
        """
        Get announcement by ID.

        Args:
            announcement_id: Announcement ID

        Returns:
            StreamingAnnouncement or None
        """
        query = """
            SELECT id, platform, guild_id, channel_id, message_id,
                   streamer_username, streamer_id, stream_id, stream_title, game_name,
                   stream_started_at, stream_ended_at, initial_viewer_count, final_viewer_count,
                   stream_duration_seconds, last_status_check_at, vod_url, vod_checked_at,
                   vod_check_attempts, created_at, updated_at
            FROM StreamingAnnouncements
            WHERE id = %s
            LIMIT 1
        """
        params = (announcement_id,)

        try:
            results = self.execute_query(query, params)
            if results and len(results) > 0:
                row = results[0]
                return StreamingAnnouncement(
                    id=row[0],
                    platform=row[1],
                    guild_id=row[2],
                    channel_id=row[3],
                    message_id=row[4],
                    streamer_username=row[5],
                    streamer_id=row[6],
                    stream_id=row[7],
                    stream_title=row[8],
                    game_name=row[9],
                    stream_started_at=row[10],
                    stream_ended_at=row[11],
                    initial_viewer_count=row[12],
                    final_viewer_count=row[13],
                    stream_duration_seconds=row[14],
                    last_status_check_at=row[15],
                    vod_url=row[16],
                    vod_checked_at=row[17],
                    vod_check_attempts=row[18],
                    created_at=row[19],
                    updated_at=row[20]
                )
            return None
        except Exception as e:
            logger.error(f"Failed to fetch announcement by ID: {e}")
            return None

    def get_active_stream_for_streamer(
        self,
        platform: str,
        guild_id: int,
        streamer_username: str
    ) -> Optional[StreamingAnnouncement]:
        """
        Get active stream announcement for specific streamer in guild.

        Args:
            platform: 'twitch' or 'youtube'
            guild_id: Discord guild ID
            streamer_username: Platform username

        Returns:
            Active announcement or None
        """
        query = """
            SELECT id, platform, guild_id, channel_id, message_id,
                   streamer_username, streamer_id, stream_id, stream_title, game_name,
                   stream_started_at, stream_ended_at, initial_viewer_count, final_viewer_count,
                   stream_duration_seconds, last_status_check_at, vod_url, vod_checked_at,
                   vod_check_attempts, created_at, updated_at
            FROM StreamingAnnouncements
            WHERE platform = %s
              AND guild_id = %s
              AND streamer_username = %s
              AND stream_ended_at IS NULL
            ORDER BY stream_started_at DESC
            LIMIT 1
        """
        params = (platform, guild_id, streamer_username)

        try:
            results = self.execute_query(query, params)
            if results and len(results) > 0:
                row = results[0]
                return StreamingAnnouncement(
                    id=row[0],
                    platform=row[1],
                    guild_id=row[2],
                    channel_id=row[3],
                    message_id=row[4],
                    streamer_username=row[5],
                    streamer_id=row[6],
                    stream_id=row[7],
                    stream_title=row[8],
                    game_name=row[9],
                    stream_started_at=row[10],
                    stream_ended_at=row[11],
                    initial_viewer_count=row[12],
                    final_viewer_count=row[13],
                    stream_duration_seconds=row[14],
                    last_status_check_at=row[15],
                    vod_url=row[16],
                    vod_checked_at=row[17],
                    vod_check_attempts=row[18],
                    created_at=row[19],
                    updated_at=row[20]
                )
            return None
        except Exception as e:
            logger.error(f"Failed to fetch active stream: {e}")
            return None

    def update_streamer_id(
        self,
        announcement_id: int,
        streamer_id: str
    ) -> bool:
        """
        Update streamer_id field (cache resolved channel ID).

        Args:
            announcement_id: Announcement ID
            streamer_id: Platform user ID

        Returns:
            True if updated successfully
        """
        query = """
            UPDATE StreamingAnnouncements
            SET
                streamer_id = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        params = (streamer_id, announcement_id)

        try:
            cursor = self.execute_query(query, params)
            if cursor and cursor.rowcount > 0:
                logger.debug(
                    f"Updated streamer_id for announcement {announcement_id}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update streamer_id: {e}")
            return False
