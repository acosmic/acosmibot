#! /usr/bin/python3.10
"""
Data Access Object for KickAnnouncement entities.
Handles database operations for Kick stream announcements and VOD tracking.
"""
from Dao.BaseDao import BaseDao
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from logger import AppLogger


logger = AppLogger(__name__).get_logger()


class KickAnnouncementDao(BaseDao):
    """
    Data Access Object for Kick stream announcements.
    Handles database operations for Kick stream announcements and VOD tracking.
    """

    def __init__(self, db=None):
        super().__init__(None, "KickAnnouncements", db)

    def create_announcement(
        self,
        guild_id: int,
        streamer_username: str,
        message_id: int,
        channel_id: int,
        stream_started_at: datetime,
        streamer_id: Optional[str] = None,
        initial_viewer_count: Optional[int] = None,
        stream_title: Optional[str] = None,
        category_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a new Kick announcement record.

        Args:
            guild_id: Discord guild ID
            streamer_username: Kick username/slug
            message_id: Discord message ID of the announcement
            channel_id: Discord channel ID where announcement was posted
            stream_started_at: When the stream started
            streamer_id: Kick user ID
            initial_viewer_count: Viewer count at time of announcement
            stream_title: Title of the stream
            category_name: Category/game being streamed

        Returns:
            int: ID of the created announcement, or None on error
        """
        sql = """
            INSERT INTO KickAnnouncements
            (guild_id, streamer_username, streamer_id, message_id, channel_id,
             stream_started_at, initial_viewer_count, stream_title, category_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            last_id = self.execute_write(
                sql,
                (guild_id, streamer_username, streamer_id, message_id, channel_id,
                 stream_started_at, initial_viewer_count, stream_title, category_name)
            )
            logger.info(f"Created Kick announcement for {streamer_username} in guild {guild_id}")
            return last_id
        except Exception as e:
            logger.error(f"Error creating Kick announcement: {e}")
            return None

    def mark_stream_offline(
        self,
        guild_id: int,
        streamer_username: str,
        final_viewer_count: Optional[int] = None,
        stream_duration_seconds: Optional[int] = None
    ) -> bool:
        """
        Mark the most recent stream as offline for a streamer in a guild.

        Args:
            guild_id: Discord guild ID
            streamer_username: Kick username
            final_viewer_count: Viewer count when stream ended
            stream_duration_seconds: Duration of the stream in seconds

        Returns:
            bool: True if updated successfully
        """
        sql = """
            UPDATE KickAnnouncements
            SET stream_ended_at = NOW(),
                final_viewer_count = %s,
                stream_duration_seconds = %s
            WHERE guild_id = %s
            AND streamer_username = %s
            AND stream_ended_at IS NULL
            ORDER BY stream_started_at DESC
            LIMIT 1
        """
        try:
            self.execute_query(
                sql,
                (final_viewer_count, stream_duration_seconds, guild_id, streamer_username),
                commit=True
            )
            logger.debug(f"Marked Kick stream offline: {streamer_username} in guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error marking Kick stream offline: {e}")
            return False

    def get_active_announcement(
        self,
        guild_id: int,
        streamer_username: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the currently active (not ended) announcement for a streamer.

        Args:
            guild_id: Discord guild ID
            streamer_username: Kick username

        Returns:
            Announcement dictionary or None
        """
        sql = """
            SELECT id, guild_id, streamer_username, streamer_id, message_id, channel_id,
                   stream_started_at, stream_title, category_name, initial_viewer_count
            FROM KickAnnouncements
            WHERE guild_id = %s
            AND streamer_username = %s
            AND stream_ended_at IS NULL
            ORDER BY stream_started_at DESC
            LIMIT 1
        """
        try:
            results = self.execute_query(sql, (guild_id, streamer_username))
            if not results:
                return None

            row = results[0]
            return {
                'id': row[0],
                'guild_id': row[1],
                'streamer_username': row[2],
                'streamer_id': row[3],
                'message_id': row[4],
                'channel_id': row[5],
                'stream_started_at': row[6],
                'stream_title': row[7],
                'category_name': row[8],
                'initial_viewer_count': row[9]
            }
        except Exception as e:
            logger.error(f"Error getting active Kick announcement: {e}")
            return None

    def get_announcements_needing_status_update(self) -> List[Dict[str, Any]]:
        """
        Get announcements for streams that need status updates (20+ minute check).
        Returns streams that:
        - Are still online (stream_ended_at IS NULL)
        - Have been live for >20 minutes
        - Have NOT been checked in last 20 minutes

        Returns:
            List of announcement dictionaries
        """
        sql = """
            SELECT id, guild_id, streamer_username, streamer_id, message_id, channel_id,
                   stream_started_at, initial_viewer_count, stream_title
            FROM KickAnnouncements
            WHERE stream_ended_at IS NULL
            AND stream_started_at < NOW() - INTERVAL 20 MINUTE
            AND (last_status_check_at IS NULL OR last_status_check_at < NOW() - INTERVAL 20 MINUTE)
            ORDER BY stream_started_at ASC
        """
        try:
            results = self.execute_query(sql)
            if not results:
                return []

            announcements = []
            for row in results:
                announcements.append({
                    'id': row[0],
                    'guild_id': row[1],
                    'streamer_username': row[2],
                    'streamer_id': row[3],
                    'message_id': row[4],
                    'channel_id': row[5],
                    'stream_started_at': row[6],
                    'initial_viewer_count': row[7],
                    'stream_title': row[8]
                })
            return announcements
        except Exception as e:
            logger.error(f"Error getting Kick announcements needing status update: {e}")
            return []

    def update_last_status_check(
        self,
        announcement_id: int,
        new_viewer_count: Optional[int] = None
    ) -> bool:
        """
        Update the last_status_check_at timestamp for an announcement.
        Optionally update the viewer count.

        Args:
            announcement_id: ID of the announcement
            new_viewer_count: Optional viewer count to update

        Returns:
            bool: True if updated successfully
        """
        if new_viewer_count is not None:
            sql = """
                UPDATE KickAnnouncements
                SET last_status_check_at = NOW(),
                    final_viewer_count = %s
                WHERE id = %s
            """
            params = (new_viewer_count, announcement_id)
        else:
            sql = """
                UPDATE KickAnnouncements
                SET last_status_check_at = NOW()
                WHERE id = %s
            """
            params = (announcement_id,)

        try:
            self.execute_query(sql, params, commit=True)
            return True
        except Exception as e:
            logger.error(f"Error updating Kick last status check: {e}")
            return False

    def get_announcements_needing_vod_check(
        self,
        hours_threshold: int = 48
    ) -> List[Dict[str, Any]]:
        """
        Get announcements that need VOD checking.
        Implements smart backoff:
        - Attempts 0-2: Check every 5 minutes
        - Attempts 3-5: Check every 15 minutes
        - Attempts >= 6: Stop checking

        Args:
            hours_threshold: Only check streams that ended within this many hours

        Returns:
            List of announcement dictionaries with vod_check_attempts included
        """
        sql = """
            SELECT id, guild_id, streamer_username, streamer_id, message_id, channel_id,
                   stream_started_at, stream_ended_at, vod_check_attempts,
                   stream_duration_seconds, final_viewer_count
            FROM KickAnnouncements
            WHERE vod_url IS NULL
            AND stream_ended_at IS NOT NULL
            AND stream_ended_at > NOW() - INTERVAL %s HOUR
            AND vod_check_attempts < 6
            AND (
                (vod_check_attempts < 3 AND (vod_checked_at IS NULL OR vod_checked_at < NOW() - INTERVAL 5 MINUTE))
                OR
                (vod_check_attempts >= 3 AND vod_checked_at < NOW() - INTERVAL 15 MINUTE)
            )
            ORDER BY stream_ended_at DESC
        """
        try:
            results = self.execute_query(sql, (hours_threshold,))
            if not results:
                return []

            announcements = []
            for row in results:
                announcements.append({
                    'id': row[0],
                    'guild_id': row[1],
                    'streamer_username': row[2],
                    'streamer_id': row[3],
                    'message_id': row[4],
                    'channel_id': row[5],
                    'stream_started_at': row[6],
                    'stream_ended_at': row[7],
                    'vod_check_attempts': row[8],
                    'stream_duration_seconds': row[9],
                    'final_viewer_count': row[10]
                })
            return announcements
        except Exception as e:
            logger.error(f"Error getting Kick announcements for VOD check: {e}")
            return []

    def update_vod_info(self, announcement_id: int, vod_url: str) -> bool:
        """
        Update announcement with VOD URL.

        Args:
            announcement_id: ID of the announcement
            vod_url: URL to the VOD

        Returns:
            bool: True if updated successfully
        """
        sql = """
            UPDATE KickAnnouncements
            SET vod_url = %s, vod_checked_at = NOW()
            WHERE id = %s
        """
        try:
            self.execute_query(sql, (vod_url, announcement_id), commit=True)
            logger.info(f"Updated Kick announcement {announcement_id} with VOD: {vod_url}")
            return True
        except Exception as e:
            logger.error(f"Error updating Kick VOD info: {e}")
            return False

    def mark_vod_checked(self, announcement_id: int) -> bool:
        """
        Mark announcement as checked for VOD (even if none found).
        Increments vod_check_attempts counter to track retry count.

        Args:
            announcement_id: ID of the announcement

        Returns:
            bool: True if updated successfully
        """
        sql = """
            UPDATE KickAnnouncements
            SET vod_checked_at = NOW(),
                vod_check_attempts = vod_check_attempts + 1
            WHERE id = %s
        """
        try:
            self.execute_query(sql, (announcement_id,), commit=True)
            return True
        except Exception as e:
            logger.error(f"Error marking Kick VOD checked: {e}")
            return False

    def get_announcement_by_id(self, announcement_id: int) -> Optional[Dict[str, Any]]:
        """
        Get announcement by ID.

        Args:
            announcement_id: ID of the announcement

        Returns:
            Announcement dictionary or None
        """
        sql = """
            SELECT id, guild_id, streamer_username, streamer_id, message_id, channel_id,
                   stream_started_at, stream_ended_at, vod_url, initial_viewer_count,
                   final_viewer_count, stream_duration_seconds, stream_title, category_name
            FROM KickAnnouncements
            WHERE id = %s
            LIMIT 1
        """
        try:
            results = self.execute_query(sql, (announcement_id,))
            if not results:
                return None

            row = results[0]
            return {
                'id': row[0],
                'guild_id': row[1],
                'streamer_username': row[2],
                'streamer_id': row[3],
                'message_id': row[4],
                'channel_id': row[5],
                'stream_started_at': row[6],
                'stream_ended_at': row[7],
                'vod_url': row[8],
                'initial_viewer_count': row[9],
                'final_viewer_count': row[10],
                'stream_duration_seconds': row[11],
                'stream_title': row[12],
                'category_name': row[13]
            }
        except Exception as e:
            logger.error(f"Error getting Kick announcement by ID: {e}")
            return None

    def get_announcement_by_message(
        self,
        guild_id: int,
        message_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get announcement by Discord message ID.

        Args:
            guild_id: Discord guild ID
            message_id: Discord message ID

        Returns:
            Announcement dictionary or None
        """
        sql = """
            SELECT id, guild_id, streamer_username, streamer_id, message_id, channel_id,
                   stream_started_at, stream_ended_at, vod_url, vod_checked_at
            FROM KickAnnouncements
            WHERE guild_id = %s AND message_id = %s
            LIMIT 1
        """
        try:
            results = self.execute_query(sql, (guild_id, message_id))
            if not results:
                return None

            row = results[0]
            return {
                'id': row[0],
                'guild_id': row[1],
                'streamer_username': row[2],
                'streamer_id': row[3],
                'message_id': row[4],
                'channel_id': row[5],
                'stream_started_at': row[6],
                'stream_ended_at': row[7],
                'vod_url': row[8],
                'vod_checked_at': row[9]
            }
        except Exception as e:
            logger.error(f"Error getting Kick announcement by message: {e}")
            return None

    def cleanup_old_announcements(self, days_threshold: int = 30) -> bool:
        """
        Clean up announcements older than threshold.

        Args:
            days_threshold: Delete announcements older than this many days

        Returns:
            bool: True if cleanup successful
        """
        sql = """
            DELETE FROM KickAnnouncements
            WHERE created_at < NOW() - INTERVAL %s DAY
        """
        try:
            self.execute_query(sql, (days_threshold,), commit=True)
            logger.info(f"Cleaned up Kick announcements older than {days_threshold} days")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up old Kick announcements: {e}")
            return False
