#! /usr/bin/python3.10
"""
GlobalSettingsDao - Data Access Object for GlobalSettings table
Handles CRUD operations for system-wide bot configuration
"""

import json
from typing import Optional, List, Dict, Any
from Dao.BaseDao import BaseDao
from Entities.GlobalSetting import GlobalSetting
from logger import AppLogger
from database import Database

logger = AppLogger(__name__).get_logger()


class GlobalSettingsDao(BaseDao[GlobalSetting]):
    """DAO for managing global bot settings"""

    def __init__(self, db: Optional[Database] = None):
        super().__init__(GlobalSetting, "GlobalSettings", db)

    def get_setting(self, setting_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific global setting by key

        Args:
            setting_key: The setting key (e.g., 'features.ai_enabled')

        Returns:
            Setting dict with key, value, category, etc., or None if not found
        """
        try:
            query = """
                SELECT id, setting_key, setting_value, category, description, updated_at, updated_by
                FROM GlobalSettings
                WHERE setting_key = %s
            """
            result = self.execute_read(query, (setting_key,))

            if result and len(result) > 0:
                row = result[0]
                return {
                    'id': row[0],
                    'setting_key': row[1],
                    'setting_value': json.loads(row[2]) if isinstance(row[2], str) else row[2],
                    'category': row[3],
                    'description': row[4],
                    'updated_at': row[5].isoformat() if row[5] else None,
                    'updated_by': row[6]
                }
            return None

        except Exception as e:
            logger.error(f"Error fetching setting {setting_key}: {e}")
            return None

    def get_setting_value(self, setting_key: str, default: Any = None) -> Any:
        """
        Get just the value of a setting

        Args:
            setting_key: The setting key
            default: Default value if setting not found

        Returns:
            Setting value or default
        """
        setting = self.get_setting(setting_key)
        if setting:
            return setting['setting_value']
        return default

    def get_all_settings(self) -> List[Dict[str, Any]]:
        """
        Get all global settings

        Returns:
            List of all setting dicts
        """
        try:
            query = """
                SELECT id, setting_key, setting_value, category, description, updated_at, updated_by
                FROM GlobalSettings
                ORDER BY category, setting_key
            """
            results = self.execute_read(query)

            settings = []
            for row in results:
                settings.append({
                    'id': row[0],
                    'setting_key': row[1],
                    'setting_value': json.loads(row[2]) if isinstance(row[2], str) else row[2],
                    'category': row[3],
                    'description': row[4],
                    'updated_at': row[5].isoformat() if row[5] else None,
                    'updated_by': row[6]
                })

            return settings

        except Exception as e:
            logger.error(f"Error fetching all settings: {e}")
            return []

    def get_settings_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get all settings in a specific category

        Args:
            category: Category name ('features', 'rate_limits', 'defaults', 'maintenance')

        Returns:
            List of setting dicts in the category
        """
        try:
            query = """
                SELECT id, setting_key, setting_value, category, description, updated_at, updated_by
                FROM GlobalSettings
                WHERE category = %s
                ORDER BY setting_key
            """
            results = self.execute_read(query, (category,))

            settings = []
            for row in results:
                settings.append({
                    'id': row[0],
                    'setting_key': row[1],
                    'setting_value': json.loads(row[2]) if isinstance(row[2], str) else row[2],
                    'category': row[3],
                    'description': row[4],
                    'updated_at': row[5].isoformat() if row[5] else None,
                    'updated_by': row[6]
                })

            return settings

        except Exception as e:
            logger.error(f"Error fetching settings for category {category}: {e}")
            return []

    def set_setting(
        self,
        setting_key: str,
        setting_value: Any,
        category: str,
        description: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> bool:
        """
        Create or update a global setting

        Args:
            setting_key: The setting key
            setting_value: The setting value (will be JSON encoded)
            category: Setting category
            description: Optional description
            updated_by: Discord ID of admin making the change

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert value to JSON string if not already
            if not isinstance(setting_value, str):
                json_value = json.dumps(setting_value)
            else:
                json_value = setting_value

            query = """
                INSERT INTO GlobalSettings
                (setting_key, setting_value, category, description, updated_by)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    setting_value = VALUES(setting_value),
                    category = VALUES(category),
                    description = VALUES(description),
                    updated_by = VALUES(updated_by),
                    updated_at = CURRENT_TIMESTAMP
            """
            result = self.execute_write(
                query,
                (setting_key, json_value, category, description, updated_by)
            )

            if result:
                logger.info(f"Updated setting {setting_key} = {setting_value}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error setting {setting_key}: {e}")
            return False

    def update_setting_value(
        self,
        setting_key: str,
        setting_value: Any,
        updated_by: Optional[str] = None
    ) -> bool:
        """
        Update only the value of an existing setting

        Args:
            setting_key: The setting key
            setting_value: New value
            updated_by: Discord ID of admin making the change

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert value to JSON string if not already
            if not isinstance(setting_value, str):
                json_value = json.dumps(setting_value)
            else:
                json_value = setting_value

            query = """
                UPDATE GlobalSettings
                SET setting_value = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP
                WHERE setting_key = %s
            """
            result = self.execute_write(query, (json_value, updated_by, setting_key))

            if result:
                logger.info(f"Updated setting value {setting_key} = {setting_value}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating setting value {setting_key}: {e}")
            return False

    def delete_setting(self, setting_key: str) -> bool:
        """
        Delete a global setting

        Args:
            setting_key: The setting key to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            query = "DELETE FROM GlobalSettings WHERE setting_key = %s"
            result = self.execute_write(query, (setting_key,))

            if result:
                logger.info(f"Deleted setting {setting_key}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting setting {setting_key}: {e}")
            return False

    def bulk_update_settings(
        self,
        settings: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> bool:
        """
        Update multiple settings at once

        Args:
            settings: Dict of setting_key: setting_value pairs
            updated_by: Discord ID of admin making changes

        Returns:
            True if all successful, False if any failed
        """
        try:
            success = True
            for key, value in settings.items():
                if not self.update_setting_value(key, value, updated_by):
                    success = False
                    logger.error(f"Failed to update setting {key} in bulk update")

            return success

        except Exception as e:
            logger.error(f"Error in bulk update settings: {e}")
            return False

    def get_all_settings_grouped(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all settings grouped by category

        Returns:
            Dict with category keys and lists of settings as values
        """
        try:
            all_settings = self.get_all_settings()
            grouped = {
                'features': [],
                'rate_limits': [],
                'defaults': [],
                'maintenance': []
            }

            for setting in all_settings:
                category = setting['category']
                if category in grouped:
                    grouped[category].append(setting)

            return grouped

        except Exception as e:
            logger.error(f"Error grouping settings: {e}")
            return {'features': [], 'rate_limits': [], 'defaults': [], 'maintenance': []}
