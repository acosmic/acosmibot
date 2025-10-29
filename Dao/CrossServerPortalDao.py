#! /usr/bin/python3.10
from typing import Optional, List
from datetime import datetime, timedelta
from database import Database
from Dao.BaseDao import BaseDao
from Entities.CrossServerPortal import CrossServerPortal


class CrossServerPortalDao(BaseDao[CrossServerPortal]):
    """
    Data Access Object for CrossServerPortal entities.
    Manages portal sessions between guilds.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the CrossServerPortalDao.

        Args:
            db: Optional database connection
        """
        super().__init__(CrossServerPortal, "CrossServerPortals", db)
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> None:
        """Create the CrossServerPortals table if it doesn't exist."""
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS CrossServerPortals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id_1 BIGINT NOT NULL,
                guild_id_2 BIGINT NOT NULL,
                channel_id_1 BIGINT NOT NULL,
                channel_id_2 BIGINT NOT NULL,
                message_id_1 BIGINT,
                message_id_2 BIGINT,
                opened_by BIGINT NOT NULL,
                cost_paid INT DEFAULT 1000,
                opened_at DATETIME NOT NULL,
                closes_at DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                INDEX idx_guild_1 (guild_id_1),
                INDEX idx_guild_2 (guild_id_2),
                INDEX idx_active (is_active),
                INDEX idx_closes_at (closes_at)
            )
        """
        self.create_table_if_not_exists(create_table_sql)

    def create_portal(self, portal: CrossServerPortal) -> Optional[CrossServerPortal]:
        """
        Create a new portal session.

        Args:
            portal: Portal to create

        Returns:
            Created portal with ID, or None on error
        """
        sql = """
            INSERT INTO CrossServerPortals (
                guild_id_1, guild_id_2, channel_id_1, channel_id_2,
                message_id_1, message_id_2, opened_by, cost_paid,
                opened_at, closes_at, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            portal.guild_id_1,
            portal.guild_id_2,
            portal.channel_id_1,
            portal.channel_id_2,
            portal.message_id_1,
            portal.message_id_2,
            portal.opened_by,
            portal.cost_paid,
            portal.opened_at,
            portal.closes_at,
            portal.is_active
        )

        try:
            result = self.execute_query(sql, values, commit=True)
            # Get the last inserted ID
            portal.id = self.get_last_insert_id()
            return portal
        except Exception as e:
            self.logger.error(f"Error creating portal: {e}")
            return None

    def get_portal_by_id(self, portal_id: int) -> Optional[CrossServerPortal]:
        """
        Get a portal by its ID.

        Args:
            portal_id: Portal ID

        Returns:
            Portal if found, None otherwise
        """
        sql = """
            SELECT id, guild_id_1, guild_id_2, channel_id_1, channel_id_2,
                   message_id_1, message_id_2, opened_by, cost_paid,
                   opened_at, closes_at, is_active
            FROM CrossServerPortals
            WHERE id = %s
        """

        try:
            result = self.execute_query(sql, (portal_id,))
            if result and len(result) > 0:
                return self._row_to_portal(result[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting portal by ID: {e}")
            return None

    def get_active_portal_for_guild(self, guild_id: int) -> Optional[CrossServerPortal]:
        """
        Get the currently active portal for a guild.

        Args:
            guild_id: Guild ID

        Returns:
            Active portal if exists, None otherwise
        """
        sql = """
            SELECT id, guild_id_1, guild_id_2, channel_id_1, channel_id_2,
                   message_id_1, message_id_2, opened_by, cost_paid,
                   opened_at, closes_at, is_active
            FROM CrossServerPortals
            WHERE (guild_id_1 = %s OR guild_id_2 = %s)
              AND is_active = TRUE
            ORDER BY opened_at DESC
            LIMIT 1
        """

        try:
            result = self.execute_query(sql, (guild_id, guild_id))
            if result and len(result) > 0:
                return self._row_to_portal(result[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting active portal for guild: {e}")
            return None

    def get_active_portal_for_channel(self, channel_id: int) -> Optional[CrossServerPortal]:
        """
        Get the active portal for a specific channel.

        Args:
            channel_id: Channel ID

        Returns:
            Active portal if exists, None otherwise
        """
        sql = """
            SELECT id, guild_id_1, guild_id_2, channel_id_1, channel_id_2,
                   message_id_1, message_id_2, opened_by, cost_paid,
                   opened_at, closes_at, is_active
            FROM CrossServerPortals
            WHERE (channel_id_1 = %s OR channel_id_2 = %s)
              AND is_active = TRUE
            LIMIT 1
        """

        try:
            result = self.execute_query(sql, (channel_id, channel_id))
            if result and len(result) > 0:
                return self._row_to_portal(result[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting active portal for channel: {e}")
            return None

    def get_all_active_portals(self) -> List[CrossServerPortal]:
        """
        Get all currently active portals.

        Returns:
            List of active portals
        """
        sql = """
            SELECT id, guild_id_1, guild_id_2, channel_id_1, channel_id_2,
                   message_id_1, message_id_2, opened_by, cost_paid,
                   opened_at, closes_at, is_active
            FROM CrossServerPortals
            WHERE is_active = TRUE
            ORDER BY opened_at DESC
        """

        try:
            results = self.execute_query(sql)
            portals = []
            if results:
                for row in results:
                    portals.append(self._row_to_portal(row))
            return portals
        except Exception as e:
            self.logger.error(f"Error getting all active portals: {e}")
            return []

    def get_expired_portals(self) -> List[CrossServerPortal]:
        """
        Get all active portals that have expired.

        Returns:
            List of expired portals that are still marked as active
        """
        sql = """
            SELECT id, guild_id_1, guild_id_2, channel_id_1, channel_id_2,
                   message_id_1, message_id_2, opened_by, cost_paid,
                   opened_at, closes_at, is_active
            FROM CrossServerPortals
            WHERE is_active = TRUE
              AND closes_at <= NOW()
        """

        try:
            results = self.execute_query(sql)
            portals = []
            if results:
                for row in results:
                    portals.append(self._row_to_portal(row))
            return portals
        except Exception as e:
            self.logger.error(f"Error getting expired portals: {e}")
            return []

    def update_portal_messages(self, portal_id: int, message_id_1: Optional[int] = None,
                                message_id_2: Optional[int] = None) -> bool:
        """
        Update portal message IDs.

        Args:
            portal_id: Portal ID
            message_id_1: First portal message ID
            message_id_2: Second portal message ID

        Returns:
            True if successful, False otherwise
        """
        updates = []
        values = []

        if message_id_1 is not None:
            updates.append("message_id_1 = %s")
            values.append(message_id_1)

        if message_id_2 is not None:
            updates.append("message_id_2 = %s")
            values.append(message_id_2)

        if not updates:
            return True

        sql = f"UPDATE CrossServerPortals SET {', '.join(updates)} WHERE id = %s"
        values.append(portal_id)

        try:
            self.execute_query(sql, tuple(values), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating portal messages: {e}")
            return False

    def close_portal(self, portal_id: int) -> bool:
        """
        Close a portal by setting it as inactive.

        Args:
            portal_id: Portal ID

        Returns:
            True if successful, False otherwise
        """
        sql = "UPDATE CrossServerPortals SET is_active = FALSE WHERE id = %s"

        try:
            self.execute_query(sql, (portal_id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error closing portal: {e}")
            return False

    def get_portal_history_for_guild(self, guild_id: int, limit: int = 10) -> List[CrossServerPortal]:
        """
        Get portal history for a guild.

        Args:
            guild_id: Guild ID
            limit: Maximum number of results

        Returns:
            List of portals (active and closed)
        """
        sql = """
            SELECT id, guild_id_1, guild_id_2, channel_id_1, channel_id_2,
                   message_id_1, message_id_2, opened_by, cost_paid,
                   opened_at, closes_at, is_active
            FROM CrossServerPortals
            WHERE guild_id_1 = %s OR guild_id_2 = %s
            ORDER BY opened_at DESC
            LIMIT %s
        """

        try:
            results = self.execute_query(sql, (guild_id, guild_id, limit))
            portals = []
            if results:
                for row in results:
                    portals.append(self._row_to_portal(row))
            return portals
        except Exception as e:
            self.logger.error(f"Error getting portal history: {e}")
            return []

    def _row_to_portal(self, row) -> CrossServerPortal:
        """
        Convert a database row to a CrossServerPortal entity.

        Args:
            row: Database row tuple

        Returns:
            CrossServerPortal entity
        """
        return CrossServerPortal(
            id=row[0],
            guild_id_1=row[1],
            guild_id_2=row[2],
            channel_id_1=row[3],
            channel_id_2=row[4],
            message_id_1=row[5],
            message_id_2=row[6],
            opened_by=row[7],
            cost_paid=row[8],
            opened_at=row[9],
            closes_at=row[10],
            is_active=row[11]
        )
