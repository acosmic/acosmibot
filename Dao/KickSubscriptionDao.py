#! /usr/bin/python3.10
"""
Data Access Object for KickSubscriptions table
Manages webhook subscription tracking with reference counting
"""
from Dao.BaseDao import BaseDao
from typing import Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class KickSubscriptionDao(BaseDao):
    """DAO for managing Kick webhook subscriptions"""

    def __init__(self):
        super().__init__(
            entity_class=None,
            table_name='KickSubscriptions'
        )

    def get_subscription_by_broadcaster(
        self,
        broadcaster_user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get subscription record for a broadcaster"""
        query = """
            SELECT id, broadcaster_user_id, broadcaster_username, subscription_id,
                   guild_count, tracked_guild_ids, subscription_status,
                   last_error, error_count, last_error_at, created_at,
                   updated_at, last_verified_at
            FROM KickSubscriptions
            WHERE broadcaster_user_id = %s
            LIMIT 1
        """
        try:
            results = self.execute_query(query, (broadcaster_user_id,))
            if results:
                return self._row_to_dict(results[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching Kick subscription for {broadcaster_user_id}: {e}")
            return None

    def get_subscription_by_username(
        self,
        broadcaster_username: str
    ) -> Optional[Dict[str, Any]]:
        """Get subscription record by broadcaster username"""
        query = """
            SELECT id, broadcaster_user_id, broadcaster_username, subscription_id,
                   guild_count, tracked_guild_ids, subscription_status,
                   last_error, error_count, last_error_at, created_at,
                   updated_at, last_verified_at
            FROM KickSubscriptions
            WHERE broadcaster_username = %s
            LIMIT 1
        """
        try:
            results = self.execute_query(query, (broadcaster_username,))
            if results:
                return self._row_to_dict(results[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching Kick subscription for username {broadcaster_username}: {e}")
            return None

    def create_subscription(
        self,
        broadcaster_user_id: str,
        broadcaster_username: str,
        guild_id: int,
        subscription_id: Optional[str] = None
    ) -> bool:
        """Create new subscription record with initial guild"""
        query = """
            INSERT INTO KickSubscriptions (
                broadcaster_user_id, broadcaster_username, subscription_id,
                guild_count, tracked_guild_ids, subscription_status
            ) VALUES (%s, %s, %s, 1, %s, %s)
        """
        guild_ids_json = json.dumps([str(guild_id)])
        status = 'active' if subscription_id else 'pending'

        try:
            self.execute_query(query, (
                broadcaster_user_id, broadcaster_username, subscription_id,
                guild_ids_json, status
            ), commit=True)
            logger.info(f"Created Kick subscription for {broadcaster_username}")
            return True
        except Exception as e:
            logger.error(f"Error creating Kick subscription: {e}")
            return False

    def add_guild_to_subscription(
        self,
        broadcaster_user_id: str,
        guild_id: int
    ) -> bool:
        """Increment reference count and add guild"""
        # First check if guild already tracked
        existing = self.get_subscription_by_broadcaster(broadcaster_user_id)
        if existing:
            tracked_guilds = existing.get('tracked_guild_ids', [])
            if str(guild_id) in tracked_guilds:
                logger.debug(f"Guild {guild_id} already tracking Kick streamer {broadcaster_user_id}")
                return True

        query = """
            UPDATE KickSubscriptions
            SET guild_count = guild_count + 1,
                tracked_guild_ids = JSON_ARRAY_APPEND(
                    COALESCE(tracked_guild_ids, '[]'), '$', %s
                ),
                updated_at = NOW()
            WHERE broadcaster_user_id = %s
        """
        try:
            self.execute_query(query, (str(guild_id), broadcaster_user_id), commit=True)
            logger.info(f"Added guild {guild_id} to Kick subscription for {broadcaster_user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding guild to Kick subscription: {e}")
            return False

    def remove_guild_from_subscription(
        self,
        broadcaster_user_id: str,
        guild_id: int
    ) -> int:
        """
        Decrement reference count and remove guild.
        Returns remaining guild count.
        """
        # Get current subscription
        subscription = self.get_subscription_by_broadcaster(broadcaster_user_id)
        if not subscription:
            return 0

        tracked_guilds = subscription.get('tracked_guild_ids', [])
        guild_id_str = str(guild_id)

        if guild_id_str not in tracked_guilds:
            return subscription.get('guild_count', 0)

        # Remove guild from list
        tracked_guilds.remove(guild_id_str)
        new_count = len(tracked_guilds)

        query = """
            UPDATE KickSubscriptions
            SET guild_count = %s,
                tracked_guild_ids = %s,
                updated_at = NOW()
            WHERE broadcaster_user_id = %s
        """
        try:
            self.execute_query(query, (
                new_count,
                json.dumps(tracked_guilds),
                broadcaster_user_id
            ), commit=True)
            logger.info(f"Removed guild {guild_id} from Kick subscription for {broadcaster_user_id}. Remaining: {new_count}")
            return new_count
        except Exception as e:
            logger.error(f"Error removing guild from Kick subscription: {e}")
            return subscription.get('guild_count', 0)

    def update_subscription_status(
        self,
        broadcaster_user_id: str,
        status: str,
        subscription_id: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        """Update subscription status and optionally subscription_id"""
        if subscription_id:
            query = """
                UPDATE KickSubscriptions
                SET subscription_status = %s,
                    subscription_id = %s,
                    last_error = %s,
                    updated_at = NOW()
                WHERE broadcaster_user_id = %s
            """
            params = (status, subscription_id, error, broadcaster_user_id)
        else:
            query = """
                UPDATE KickSubscriptions
                SET subscription_status = %s,
                    last_error = %s,
                    error_count = error_count + 1,
                    last_error_at = NOW(),
                    updated_at = NOW()
                WHERE broadcaster_user_id = %s
            """
            params = (status, error, broadcaster_user_id)

        try:
            self.execute_query(query, params, commit=True)
            return True
        except Exception as e:
            logger.error(f"Error updating Kick subscription status: {e}")
            return False

    def delete_subscription(self, broadcaster_user_id: str) -> bool:
        """Delete subscription record"""
        query = "DELETE FROM KickSubscriptions WHERE broadcaster_user_id = %s"
        try:
            self.execute_query(query, (broadcaster_user_id,), commit=True)
            logger.info(f"Deleted Kick subscription for {broadcaster_user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting Kick subscription: {e}")
            return False

    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all active subscriptions"""
        query = """
            SELECT id, broadcaster_user_id, broadcaster_username, subscription_id,
                   guild_count, tracked_guild_ids, subscription_status
            FROM KickSubscriptions
            WHERE guild_count > 0
        """
        try:
            results = self.execute_query(query)
            return [self._row_to_dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Error getting all Kick subscriptions: {e}")
            return []

    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        tracked_ids = row[5]
        if isinstance(tracked_ids, str):
            tracked_ids = json.loads(tracked_ids)
        elif tracked_ids is None:
            tracked_ids = []

        return {
            'id': row[0],
            'broadcaster_user_id': row[1],
            'broadcaster_username': row[2],
            'subscription_id': row[3],
            'guild_count': row[4],
            'tracked_guild_ids': tracked_ids,
            'subscription_status': row[6],
            'last_error': row[7] if len(row) > 7 else None,
            'error_count': row[8] if len(row) > 8 else 0,
            'last_error_at': row[9] if len(row) > 9 else None,
            'created_at': row[10] if len(row) > 10 else None,
            'updated_at': row[11] if len(row) > 11 else None,
            'last_verified_at': row[12] if len(row) > 12 else None
        }
