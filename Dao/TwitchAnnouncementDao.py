#! /usr/bin/python3.10
from Dao.BaseDao import BaseDao
from Entities.TwitchAnnouncement import TwitchAnnouncement
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from logger import AppLogger


logger = AppLogger(__name__).get_logger()


class TwitchAnnouncementDao(BaseDao[TwitchAnnouncement]):
    """
    Data Access Object for TwitchAnnouncement entities.
    Handles database operations for Twitch stream announcements and VOD tracking.
    """

    def __init__(self, db=None):
        super().__init__(TwitchAnnouncement, "TwitchAnnouncements", db)

    def create_table(self):
        """Create the TwitchAnnouncements table if it doesn't exist"""
        sql = """
            CREATE TABLE IF NOT EXISTS TwitchAnnouncements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                streamer_username VARCHAR(100) NOT NULL,
                message_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                stream_started_at DATETIME NOT NULL,
                stream_ended_at DATETIME NULL,
                vod_url VARCHAR(500) NULL,
                vod_checked_at DATETIME NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_guild_streamer (guild_id, streamer_username),
                INDEX idx_message (guild_id, message_id),
                INDEX idx_vod_check (vod_url, vod_checked_at),
                INDEX idx_stream_ended (stream_ended_at, vod_url)
            )
        """
        try:
            self.execute_query(sql, commit=True)
            logger.info("TwitchAnnouncements table created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating TwitchAnnouncements table: {e}")
            return False

    def create_announcement(
        self,
        guild_id: int,
        streamer_username: str,
        message_id: int,
        channel_id: int,
        stream_started_at: datetime,
        initial_viewer_count: Optional[int] = None,
        stream_title: Optional[str] = None,
        game_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a new announcement record.

        Args:
            guild_id: Discord guild ID
            streamer_username: Twitch username
            message_id: Discord message ID of the announcement
            channel_id: Discord channel ID where announcement was posted
            stream_started_at: When the stream started
            initial_viewer_count: Viewer count at time of announcement
            stream_title: Title of the stream
            game_name: Game/category being streamed

        Returns:
            int: ID of the created announcement, or None on error
        """
        sql = """
            INSERT INTO TwitchAnnouncements
            (guild_id, streamer_username, message_id, channel_id, stream_started_at,
             initial_viewer_count, stream_title, game_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            self.execute_query(
                sql,
                (guild_id, streamer_username, message_id, channel_id, stream_started_at,
                 initial_viewer_count, stream_title, game_name),
                commit=True
            )
            # Get the last inserted ID
            cursor = self.db.mydb.cursor()
            cursor.execute("SELECT LAST_INSERT_ID()")
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error creating announcement: {e}")
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
            streamer_username: Twitch username
            final_viewer_count: Viewer count when stream ended
            stream_duration_seconds: Duration of the stream in seconds

        Returns:
            bool: True if updated successfully
        """
        sql = """
            UPDATE TwitchAnnouncements
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
            logger.debug(f"Marked stream offline: {streamer_username} in guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error marking stream offline: {e}")
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
            SELECT id, guild_id, streamer_username, message_id, channel_id,
                   stream_started_at, stream_ended_at, vod_check_attempts
            FROM TwitchAnnouncements
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
                    'message_id': row[3],
                    'channel_id': row[4],
                    'stream_started_at': row[5],
                    'stream_ended_at': row[6],
                    'vod_check_attempts': row[7]
                })
            return announcements
        except Exception as e:
            logger.error(f"Error getting announcements for VOD check: {e}")
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
            UPDATE TwitchAnnouncements
            SET vod_url = %s, vod_checked_at = NOW()
            WHERE id = %s
        """
        try:
            self.execute_query(sql, (vod_url, announcement_id), commit=True)
            logger.info(f"Updated announcement {announcement_id} with VOD: {vod_url}")
            return True
        except Exception as e:
            logger.error(f"Error updating VOD info: {e}")
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
            UPDATE TwitchAnnouncements
            SET vod_checked_at = NOW(),
                vod_check_attempts = vod_check_attempts + 1
            WHERE id = %s
        """
        try:
            self.execute_query(sql, (announcement_id,), commit=True)
            return True
        except Exception as e:
            logger.error(f"Error marking VOD checked: {e}")
            return False

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
            SELECT id, guild_id, streamer_username, message_id, channel_id,
                   stream_started_at, stream_ended_at, vod_url, vod_checked_at
            FROM TwitchAnnouncements
            WHERE guild_id = %s AND message_id = %s
            LIMIT 1
        """
        try:
            results = self.execute_query(sql, (guild_id, message_id))
            if not results or len(results) == 0:
                return None

            row = results[0]
            return {
                'id': row[0],
                'guild_id': row[1],
                'streamer_username': row[2],
                'message_id': row[3],
                'channel_id': row[4],
                'stream_started_at': row[5],
                'stream_ended_at': row[6],
                'vod_url': row[7],
                'vod_checked_at': row[8]
            }
        except Exception as e:
            logger.error(f"Error getting announcement by message: {e}")
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
            DELETE FROM TwitchAnnouncements
            WHERE created_at < NOW() - INTERVAL %s DAY
        """
        try:
            self.execute_query(sql, (days_threshold,), commit=True)
            logger.info(f"Cleaned up announcements older than {days_threshold} days")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up old announcements: {e}")
            return False

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
            SELECT id, guild_id, streamer_username, message_id, channel_id,
                   stream_started_at, initial_viewer_count
            FROM TwitchAnnouncements
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
                    'message_id': row[3],
                    'channel_id': row[4],
                    'stream_started_at': row[5],
                    'initial_viewer_count': row[6]
                })
            return announcements
        except Exception as e:
            logger.error(f"Error getting announcements needing status update: {e}")
            return []

    def update_last_status_check(self, announcement_id: int) -> bool:
        """
        Update the last_status_check_at timestamp for an announcement.

        Args:
            announcement_id: ID of the announcement

        Returns:
            bool: True if updated successfully
        """
        sql = """
            UPDATE TwitchAnnouncements
            SET last_status_check_at = NOW()
            WHERE id = %s
        """
        try:
            self.execute_query(sql, (announcement_id,), commit=True)
            return True
        except Exception as e:
            logger.error(f"Error updating last status check: {e}")
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
            SELECT id, guild_id, streamer_username, message_id, channel_id,
                   stream_started_at, stream_ended_at, vod_url, initial_viewer_count,
                   final_viewer_count, stream_duration_seconds, stream_title, game_name
            FROM TwitchAnnouncements
            WHERE id = %s
            LIMIT 1
        """
        try:
            results = self.execute_query(sql, (announcement_id,))
            if not results or len(results) == 0:
                return None

            row = results[0]
            return {
                'id': row[0],
                'guild_id': row[1],
                'streamer_username': row[2],
                'message_id': row[3],
                'channel_id': row[4],
                'stream_started_at': row[5],
                'stream_ended_at': row[6],
                'vod_url': row[7],
                'initial_viewer_count': row[8],
                'final_viewer_count': row[9],
                'stream_duration_seconds': row[10],
                'stream_title': row[11],
                'game_name': row[12]
            }
        except Exception as e:
            logger.error(f"Error getting announcement by ID: {e}")
            return None
