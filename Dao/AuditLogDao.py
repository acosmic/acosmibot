#! /usr/bin/python3.10
"""
AuditLogDao - Data Access Object for AuditLog table
Handles logging and retrieval of administrative actions
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from Dao.BaseDao import BaseDao
from Entities.AuditLog import AuditLog
from logger import AppLogger
from database import Database

logger = AppLogger(__name__).get_logger()


class AuditLogDao(BaseDao[AuditLog]):
    """DAO for managing audit logs"""

    def __init__(self, db: Optional[Database] = None):
        super().__init__(AuditLog, "AuditLog", db)

    def log_action(
        self,
        admin_id: str,
        admin_username: str,
        action_type: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> Optional[int]:
        """
        Log an administrative action

        Args:
            admin_id: Discord ID of admin performing action
            admin_username: Username of admin
            action_type: Type of action (e.g., 'update_setting', 'blacklist_guild')
            target_type: Type of entity affected (e.g., 'guild', 'user', 'setting')
            target_id: ID of affected entity
            changes: Dict of changes made
            ip_address: IP address of admin

        Returns:
            ID of created log entry, or None on failure
        """
        try:
            # Convert changes dict to JSON string
            changes_json = json.dumps(changes) if changes else None

            query = """
                INSERT INTO AuditLog
                (admin_id, admin_username, action_type, target_type, target_id, changes, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            result = self.execute_write(
                query,
                (admin_id, admin_username, action_type, target_type, target_id, changes_json, ip_address)
            )

            if result:
                logger.info(f"Logged action: {action_type} by {admin_username} ({admin_id})")
                return result
            return None

        except Exception as e:
            logger.error(f"Error logging action: {e}")
            return None

    def get_recent_logs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get recent audit logs

        Args:
            limit: Maximum number of logs to return
            offset: Offset for pagination

        Returns:
            List of audit log dicts
        """
        try:
            query = """
                SELECT id, admin_id, admin_username, action_type, target_type, target_id,
                       changes, ip_address, timestamp
                FROM AuditLog
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            results = self.execute_read(query, (limit, offset))

            logs = []
            for row in results:
                logs.append({
                    'id': row[0],
                    'admin_id': row[1],
                    'admin_username': row[2],
                    'action_type': row[3],
                    'target_type': row[4],
                    'target_id': row[5],
                    'changes': json.loads(row[6]) if row[6] else None,
                    'ip_address': row[7],
                    'timestamp': row[8].isoformat() if row[8] else None
                })

            return logs

        except Exception as e:
            logger.error(f"Error fetching recent logs: {e}")
            return []

    def get_logs_by_admin(
        self,
        admin_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for a specific admin

        Args:
            admin_id: Discord ID of admin
            limit: Maximum number of logs to return
            offset: Offset for pagination

        Returns:
            List of audit log dicts
        """
        try:
            query = """
                SELECT id, admin_id, admin_username, action_type, target_type, target_id,
                       changes, ip_address, timestamp
                FROM AuditLog
                WHERE admin_id = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            results = self.execute_read(query, (admin_id, limit, offset))

            logs = []
            for row in results:
                logs.append({
                    'id': row[0],
                    'admin_id': row[1],
                    'admin_username': row[2],
                    'action_type': row[3],
                    'target_type': row[4],
                    'target_id': row[5],
                    'changes': json.loads(row[6]) if row[6] else None,
                    'ip_address': row[7],
                    'timestamp': row[8].isoformat() if row[8] else None
                })

            return logs

        except Exception as e:
            logger.error(f"Error fetching logs for admin {admin_id}: {e}")
            return []

    def get_logs_by_action_type(
        self,
        action_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for a specific action type

        Args:
            action_type: Type of action to filter by
            limit: Maximum number of logs to return
            offset: Offset for pagination

        Returns:
            List of audit log dicts
        """
        try:
            query = """
                SELECT id, admin_id, admin_username, action_type, target_type, target_id,
                       changes, ip_address, timestamp
                FROM AuditLog
                WHERE action_type = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            results = self.execute_read(query, (action_type, limit, offset))

            logs = []
            for row in results:
                logs.append({
                    'id': row[0],
                    'admin_id': row[1],
                    'admin_username': row[2],
                    'action_type': row[3],
                    'target_type': row[4],
                    'target_id': row[5],
                    'changes': json.loads(row[6]) if row[6] else None,
                    'ip_address': row[7],
                    'timestamp': row[8].isoformat() if row[8] else None
                })

            return logs

        except Exception as e:
            logger.error(f"Error fetching logs for action type {action_type}: {e}")
            return []

    def get_logs_by_target(
        self,
        target_type: str,
        target_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for a specific target

        Args:
            target_type: Type of target entity
            target_id: ID of target entity
            limit: Maximum number of logs to return
            offset: Offset for pagination

        Returns:
            List of audit log dicts
        """
        try:
            query = """
                SELECT id, admin_id, admin_username, action_type, target_type, target_id,
                       changes, ip_address, timestamp
                FROM AuditLog
                WHERE target_type = %s AND target_id = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            results = self.execute_read(query, (target_type, target_id, limit, offset))

            logs = []
            for row in results:
                logs.append({
                    'id': row[0],
                    'admin_id': row[1],
                    'admin_username': row[2],
                    'action_type': row[3],
                    'target_type': row[4],
                    'target_id': row[5],
                    'changes': json.loads(row[6]) if row[6] else None,
                    'ip_address': row[7],
                    'timestamp': row[8].isoformat() if row[8] else None
                })

            return logs

        except Exception as e:
            logger.error(f"Error fetching logs for target {target_type}:{target_id}: {e}")
            return []

    def get_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs within a date range

        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of logs to return
            offset: Offset for pagination

        Returns:
            List of audit log dicts
        """
        try:
            query = """
                SELECT id, admin_id, admin_username, action_type, target_type, target_id,
                       changes, ip_address, timestamp
                FROM AuditLog
                WHERE timestamp BETWEEN %s AND %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            results = self.execute_read(query, (start_date, end_date, limit, offset))

            logs = []
            for row in results:
                logs.append({
                    'id': row[0],
                    'admin_id': row[1],
                    'admin_username': row[2],
                    'action_type': row[3],
                    'target_type': row[4],
                    'target_id': row[5],
                    'changes': json.loads(row[6]) if row[6] else None,
                    'ip_address': row[7],
                    'timestamp': row[8].isoformat() if row[8] else None
                })

            return logs

        except Exception as e:
            logger.error(f"Error fetching logs by date range: {e}")
            return []

    def get_log_count(self) -> int:
        """
        Get total count of audit logs

        Returns:
            Total number of audit log entries
        """
        try:
            query = "SELECT COUNT(*) FROM AuditLog"
            result = self.execute_read(query)

            if result and len(result) > 0:
                return result[0][0]
            return 0

        except Exception as e:
            logger.error(f"Error getting log count: {e}")
            return 0

    def delete_old_logs(self, days_to_keep: int = 90) -> int:
        """
        Delete audit logs older than specified days

        Args:
            days_to_keep: Number of days of logs to retain

        Returns:
            Number of logs deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            query = "DELETE FROM AuditLog WHERE timestamp < %s"
            result = self.execute_write(query, (cutoff_date,))

            if result:
                logger.info(f"Deleted audit logs older than {days_to_keep} days")
                return result
            return 0

        except Exception as e:
            logger.error(f"Error deleting old logs: {e}")
            return 0

    def search_logs(
        self,
        search_term: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search audit logs by admin username, action type, or target ID

        Args:
            search_term: Term to search for
            limit: Maximum number of logs to return
            offset: Offset for pagination

        Returns:
            List of matching audit log dicts
        """
        try:
            search_pattern = f"%{search_term}%"
            query = """
                SELECT id, admin_id, admin_username, action_type, target_type, target_id,
                       changes, ip_address, timestamp
                FROM AuditLog
                WHERE admin_username LIKE %s
                   OR action_type LIKE %s
                   OR target_id LIKE %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            results = self.execute_read(query, (search_pattern, search_pattern, search_pattern, limit, offset))

            logs = []
            for row in results:
                logs.append({
                    'id': row[0],
                    'admin_id': row[1],
                    'admin_username': row[2],
                    'action_type': row[3],
                    'target_type': row[4],
                    'target_id': row[5],
                    'changes': json.loads(row[6]) if row[6] else None,
                    'ip_address': row[7],
                    'timestamp': row[8].isoformat() if row[8] else None
                })

            return logs

        except Exception as e:
            logger.error(f"Error searching logs: {e}")
            return []
