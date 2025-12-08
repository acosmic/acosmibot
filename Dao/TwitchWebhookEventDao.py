#! /usr/bin/python3.10
"""
Data Access Object for TwitchWebhookEvents table
Tracks webhook events for idempotency and debugging
"""
from Dao.BaseDao import BaseDao
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class TwitchWebhookEventDao(BaseDao):
    """DAO for tracking Twitch webhook events"""

    def __init__(self):
        super().__init__(
            entity_class=None,
            table_name='TwitchWebhookEvents'
        )

    def event_exists(self, event_id: str) -> bool:
        """Check if event has already been processed (idempotency)"""
        query = "SELECT 1 FROM TwitchWebhookEvents WHERE event_id = %s LIMIT 1"

        try:
            results = self.execute_query(query, (event_id,))
            return bool(results)
        except Exception as e:
            logger.error(f"Error checking event existence: {e}")
            return False

    def create_event(
        self,
        event_id: str,
        event_type: str,
        subscription_id: str,
        broadcaster_user_id: str,
        broadcaster_username: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """Record incoming webhook event"""
        query = """
            INSERT INTO TwitchWebhookEvents (
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
            ))
            logger.info(f"Recorded webhook event {event_id} ({event_type}) for {broadcaster_username}")
            return True
        except Exception as e:
            logger.error(f"Error creating webhook event record: {e}")
            return False

    def mark_event_processed(
        self,
        event_id: str,
        error: Optional[str] = None
    ) -> bool:
        """Mark event as processed (with optional error)"""
        if error:
            query = """
                UPDATE TwitchWebhookEvents
                SET processed = TRUE, processed_at = NOW(), processing_error = %s
                WHERE event_id = %s
            """
            params = (error, event_id)
        else:
            query = """
                UPDATE TwitchWebhookEvents
                SET processed = TRUE, processed_at = NOW()
                WHERE event_id = %s
            """
            params = (event_id,)

        try:
            self.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error marking event processed: {e}")
            return False

    def cleanup_old_events(self, days: int = 7) -> int:
        """Delete events older than specified days"""
        query = "DELETE FROM TwitchWebhookEvents WHERE received_at < DATE_SUB(NOW(), INTERVAL %s DAY)"

        try:
            cursor = self.execute_query(query, (days,))
            deleted_count = cursor.rowcount if cursor else 0
            logger.info(f"Cleaned up {deleted_count} old webhook events")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}")
            return 0
