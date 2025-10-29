#! /usr/bin/python3.10
"""
AdminUserDao - Data Access Object for AdminUsers table
Handles CRUD operations for bot administrators
"""

from typing import Optional, List, Dict, Any
from Dao.BaseDao import BaseDao
from Entities.AdminUser import AdminUser
from logger import AppLogger
from database import Database

logger = AppLogger(__name__).get_logger()


class AdminUserDao(BaseDao[AdminUser]):
    """DAO for managing bot administrators"""

    def __init__(self, db: Optional[Database] = None):
        super().__init__(AdminUser, "AdminUsers", db)

    def create_admin(
        self,
        discord_id: str,
        discord_username: str,
        role: str = "admin",
        created_by: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a new admin user

        Args:
            discord_id: Discord user ID
            discord_username: Discord username
            role: Admin role ('super_admin' or 'admin')
            created_by: Discord ID of admin who created this user

        Returns:
            ID of created admin user, or None on failure
        """
        try:
            query = """
                INSERT INTO AdminUsers
                (discord_id, discord_username, role, created_by)
                VALUES (%s, %s, %s, %s)
            """
            result = self.execute_write(query, (discord_id, discord_username, role, created_by))

            if result:
                logger.info(f"Created admin user: {discord_username} ({discord_id}) with role {role}")
                return result
            return None

        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            return None

    def get_admin_by_discord_id(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """
        Get admin user by Discord ID

        Args:
            discord_id: Discord user ID

        Returns:
            Admin user dict or None if not found
        """
        try:
            query = """
                SELECT id, discord_id, discord_username, role, created_at, created_by
                FROM AdminUsers
                WHERE discord_id = %s
            """
            result = self.execute_read(query, (discord_id,))

            if result and len(result) > 0:
                row = result[0]
                return {
                    'id': row[0],
                    'discord_id': row[1],
                    'discord_username': row[2],
                    'role': row[3],
                    'created_at': row[4].isoformat() if row[4] else None,
                    'created_by': row[5]
                }
            return None

        except Exception as e:
            logger.error(f"Error fetching admin by discord_id {discord_id}: {e}")
            return None

    def is_admin(self, discord_id: str) -> bool:
        """
        Check if a Discord user is an admin

        Args:
            discord_id: Discord user ID

        Returns:
            True if user is an admin, False otherwise
        """
        admin = self.get_admin_by_discord_id(discord_id)
        return admin is not None

    def is_super_admin(self, discord_id: str) -> bool:
        """
        Check if a Discord user is a super admin

        Args:
            discord_id: Discord user ID

        Returns:
            True if user is a super admin, False otherwise
        """
        admin = self.get_admin_by_discord_id(discord_id)
        return admin is not None and admin['role'] == 'super_admin'

    def get_all_admins(self) -> List[Dict[str, Any]]:
        """
        Get all admin users

        Returns:
            List of admin user dicts
        """
        try:
            query = """
                SELECT id, discord_id, discord_username, role, created_at, created_by
                FROM AdminUsers
                ORDER BY created_at DESC
            """
            results = self.execute_read(query)

            admins = []
            for row in results:
                admins.append({
                    'id': row[0],
                    'discord_id': row[1],
                    'discord_username': row[2],
                    'role': row[3],
                    'created_at': row[4].isoformat() if row[4] else None,
                    'created_by': row[5]
                })

            return admins

        except Exception as e:
            logger.error(f"Error fetching all admins: {e}")
            return []

    def update_admin_role(self, discord_id: str, new_role: str) -> bool:
        """
        Update an admin's role

        Args:
            discord_id: Discord user ID
            new_role: New role ('super_admin' or 'admin')

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            query = """
                UPDATE AdminUsers
                SET role = %s
                WHERE discord_id = %s
            """
            result = self.execute_write(query, (new_role, discord_id))

            if result:
                logger.info(f"Updated admin role for {discord_id} to {new_role}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating admin role: {e}")
            return False

    def delete_admin(self, discord_id: str) -> bool:
        """
        Delete an admin user

        Args:
            discord_id: Discord user ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            query = "DELETE FROM AdminUsers WHERE discord_id = %s"
            result = self.execute_write(query, (discord_id,))

            if result:
                logger.info(f"Deleted admin user: {discord_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting admin: {e}")
            return False

    def update_admin_username(self, discord_id: str, new_username: str) -> bool:
        """
        Update an admin's Discord username

        Args:
            discord_id: Discord user ID
            new_username: New Discord username

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            query = """
                UPDATE AdminUsers
                SET discord_username = %s
                WHERE discord_id = %s
            """
            result = self.execute_write(query, (new_username, discord_id))

            if result:
                logger.info(f"Updated admin username for {discord_id} to {new_username}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating admin username: {e}")
            return False
