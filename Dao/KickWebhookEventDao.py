#! /usr/bin/python3.10
"""
Data Access Object for KickWebhookEvents table
Tracks webhook events for idempotency and debugging
"""
from Dao.BaseDao import BaseDao
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class KickWebhookEventDao(BaseDao):
    """DAO for tracking Kick webhook events"""

    def __init__(self):
        super().__init__(
            entity_class=None,
            table_name='KickWebhookEvents'
        )

    def event_exists(self, event_id: str) -> bool:
        """Check if event has already been processed (idempotency)"""
        query = "SELECT 1 FROM KickWebhookEvents WHERE event_id = %s LIMIT 1"

        try:
            results = self.execute_query(query, (event_id,))
            return bool(results)
        except Exception as e:
            logger.error(f"Error checking Kick event existence: {e}")
            return False

    def create_event(
        self,
        event_id: str,
        event_type: str,
        subscription_id: Optional[str],
        broadcaster_user_id: Optional[str],
        broadcaster_username: Optional[str],
        event_data: Dict[str, Any]
    ) -> bool:
        """Record incoming webhook event"""
        query = """
            INSERT INTO KickWebhookEvents (
                event_id,
                event_type,
                subscription_id,
                broadcaster_user_id,
                broadcaster_username,
                event_data
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """

        try:
            self.execute_query(query, (
                event_id,
                event_type,
                subscription_id,
                broadcaster_user_id,
                broadcaster_username,
                json.dumps(event_data)
            ), commit=True)
            logger.info(f"Recorded Kick webhook event {event_id} ({event_type}) for {broadcaster_username}")
            return True
        except Exception as e:
            logger.error(f"Error creating Kick webhook event record: {e}")
            return False

    def mark_event_processed(
        self,
        event_id: str,
        error: Optional[str] = None
    ) -> bool:
        """Mark event as processed (with optional error)"""
        if error:
            query = """
                UPDATE KickWebhookEvents
                SET processed_at = NOW(), process_error = %s
                WHERE event_id = %s
            """
            params = (error, event_id)
        else:
            query = """
                UPDATE KickWebhookEvents
                SET processed_at = NOW()
                WHERE event_id = %s
            """
            params = (event_id,)

        try:
            self.execute_query(query, params, commit=True)
            return True
        except Exception as e:
            logger.error(f"Error marking Kick event processed: {e}")
            return False

    def cleanup_old_events(self, days: int = 7) -> int:
        """Delete events older than specified days"""
        query = "DELETE FROM KickWebhookEvents WHERE received_at < DATE_SUB(NOW(), INTERVAL %s DAY)"

        try:
            cursor = self.execute_query(query, (days,), commit=True)
            deleted_count = cursor.rowcount if cursor else 0
            logger.info(f"Cleaned up {deleted_count} old Kick webhook events")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old Kick events: {e}")
            return 0
