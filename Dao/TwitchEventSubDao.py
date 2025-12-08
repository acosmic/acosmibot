#! /usr/bin/python3.10
"""
Data Access Object for TwitchEventSubSubscriptions table
Manages EventSub subscription tracking with reference counting
"""
from Dao.BaseDao import BaseDao
from typing import Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class TwitchEventSubDao(BaseDao):
    """DAO for managing Twitch EventSub subscriptions"""

    def __init__(self):
        super().__init__(
            entity_class=None,  # We'll use dicts for simplicity
            table_name='TwitchEventSubSubscriptions'
        )

    def get_subscription_by_broadcaster(
        self,
        broadcaster_user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get subscription record for a broadcaster"""
        query = """
            SELECT * FROM TwitchEventSubSubscriptions
            WHERE broadcaster_user_id = %s
            LIMIT 1
        """
        try:
            results = self.execute_query(query, (broadcaster_user_id,))
            if results:
                return self._row_to_dict(results[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching subscription for {broadcaster_user_id}: {e}")
            return None

    def create_subscription(
        self,
        broadcaster_user_id: str,
        broadcaster_username: str,
        guild_id: int,
        online_subscription_id: Optional[str] = None,
        offline_subscription_id: Optional[str] = None
    ) -> bool:
        """Create new subscription record with initial guild"""
        query = """
            INSERT INTO TwitchEventSubSubscriptions (
                broadcaster_user_id,
                broadcaster_username,
                online_subscription_id,
                offline_subscription_id,
                guild_count,
                tracked_guild_ids,
                online_status,
                offline_status
            ) VALUES (%s, %s, %s, %s, 1, %s, %s, %s)
        """

        guild_ids_json = json.dumps([str(guild_id)])
        online_status = 'active' if online_subscription_id else 'pending'
        offline_status = 'active' if offline_subscription_id else 'pending'

        try:
            self.execute_query(query, (
                broadcaster_user_id,
                broadcaster_username,
                online_subscription_id,
                offline_subscription_id,
                guild_ids_json,
                online_status,
                offline_status
            ))
            logger.info(f"Created EventSub subscription record for {broadcaster_username}")
            return True
        except Exception as e:
            logger.error(f"Error creating subscription record: {e}")
            return False

    def add_guild_to_subscription(
        self,
        broadcaster_user_id: str,
        guild_id: int
    ) -> bool:
        """Increment reference count and add guild to tracking list"""
        query = """
            UPDATE TwitchEventSubSubscriptions
            SET
                guild_count = guild_count + 1,
                tracked_guild_ids = JSON_ARRAY_APPEND(
                    COALESCE(tracked_guild_ids, '[]'),
                    '$',
                    %s
                ),
                updated_at = NOW()
            WHERE broadcaster_user_id = %s
        """

        try:
            cursor = self.execute_query(query, (str(guild_id), broadcaster_user_id))
            if cursor and cursor.rowcount > 0:
                logger.info(f"Added guild {guild_id} to subscription for {broadcaster_user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding guild to subscription: {e}")
            return False

    def remove_guild_from_subscription(
        self,
        broadcaster_user_id: str,
        guild_id: int
    ) -> int:
        """
        Decrement reference count and remove guild from tracking list

        Returns:
            Remaining guild_count (0 means should delete subscription)
        """
        # First, remove the guild ID from the JSON array and decrement count
        query = """
            UPDATE TwitchEventSubSubscriptions
            SET
                guild_count = GREATEST(guild_count - 1, 0),
                tracked_guild_ids = JSON_REMOVE(
                    tracked_guild_ids,
                    JSON_UNQUOTE(JSON_SEARCH(tracked_guild_ids, 'one', %s))
                ),
                updated_at = NOW()
            WHERE broadcaster_user_id = %s
        """

        try:
            self.execute_query(query, (str(guild_id), broadcaster_user_id))

            # Fetch updated guild_count
            count_query = "SELECT guild_count FROM TwitchEventSubSubscriptions WHERE broadcaster_user_id = %s"
            result = self.execute_query(count_query, (broadcaster_user_id,))

            if result:
                remaining_count = result[0][0]
                logger.info(f"Removed guild {guild_id} from subscription for {broadcaster_user_id}. Remaining: {remaining_count}")
                return remaining_count
            return 0
        except Exception as e:
            logger.error(f"Error removing guild from subscription: {e}")
            return -1  # Error indicator

    def update_subscription_ids(
        self,
        broadcaster_user_id: str,
        online_subscription_id: Optional[str] = None,
        offline_subscription_id: Optional[str] = None
    ) -> bool:
        """Update EventSub subscription IDs after creation"""
        updates = []
        params = []

        if online_subscription_id:
            updates.append("online_subscription_id = %s, online_status = 'active'")
            params.append(online_subscription_id)

        if offline_subscription_id:
            updates.append("offline_subscription_id = %s, offline_status = 'active'")
            params.append(offline_subscription_id)

        if not updates:
            return False

        params.append(broadcaster_user_id)
        query = f"""
            UPDATE TwitchEventSubSubscriptions
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE broadcaster_user_id = %s
        """

        try:
            cursor = self.execute_query(query, tuple(params))
            return cursor and cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating subscription IDs: {e}")
            return False

    def delete_subscription(
        self,
        broadcaster_user_id: str
    ) -> bool:
        """Delete subscription record"""
        query = "DELETE FROM TwitchEventSubSubscriptions WHERE broadcaster_user_id = %s"

        try:
            cursor = self.execute_query(query, (broadcaster_user_id,))
            if cursor and cursor.rowcount > 0:
                logger.info(f"Deleted subscription record for {broadcaster_user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting subscription: {e}")
            return False

    def get_all_active_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all subscriptions with guild_count > 0"""
        query = """
            SELECT * FROM TwitchEventSubSubscriptions
            WHERE guild_count > 0
            ORDER BY broadcaster_username
        """

        try:
            results = self.execute_query(query)
            return [self._row_to_dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error fetching active subscriptions: {e}")
            return []

    def mark_subscription_error(
        self,
        broadcaster_user_id: str,
        error_message: str,
        subscription_type: str = 'both'  # 'online', 'offline', or 'both'
    ) -> bool:
        """Mark subscription as failed with error details"""
        status_updates = []
        if subscription_type in ['online', 'both']:
            status_updates.append("online_status = 'failed'")
        if subscription_type in ['offline', 'both']:
            status_updates.append("offline_status = 'failed'")

        query = f"""
            UPDATE TwitchEventSubSubscriptions
            SET
                {', '.join(status_updates)},
                last_error = %s,
                error_count = error_count + 1,
                last_error_at = NOW(),
                updated_at = NOW()
            WHERE broadcaster_user_id = %s
        """

        try:
            self.execute_query(query, (error_message, broadcaster_user_id))
            logger.warning(f"Marked subscription as failed for {broadcaster_user_id}: {error_message}")
            return True
        except Exception as e:
            logger.error(f"Error marking subscription error: {e}")
            return False

    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        return {
            'id': row[0],
            'broadcaster_user_id': row[1],
            'broadcaster_username': row[2],
            'online_subscription_id': row[3],
            'offline_subscription_id': row[4],
            'guild_count': row[5],
            'tracked_guild_ids': json.loads(row[6]) if row[6] else [],
            'online_status': row[7],
            'offline_status': row[8],
            'last_error': row[9],
            'error_count': row[10],
            'last_error_at': row[11],
            'created_at': row[12],
            'updated_at': row[13],
            'last_verified_at': row[14]
        }
