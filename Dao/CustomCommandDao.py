#! /usr/bin/python3.10
"""Data Access Object for CustomCommand entity"""
from typing import Optional, List, Dict, Any
import json
from Dao.BaseDao import BaseDao
from Entities.CustomCommand import CustomCommand
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class CustomCommandDao(BaseDao):
    """DAO for managing custom commands"""

    def __init__(self):
        super().__init__(table_name="CustomCommands", entity_class=CustomCommand)
        self.table_name = "CustomCommands"

    def create_command(
        self,
        guild_id: str,
        command: str,
        created_by: str,
        prefix: str = '!',
        response_type: str = 'text',
        response_text: Optional[str] = None,
        embed_config: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Create a new custom command

        Args:
            guild_id: Discord guild ID
            command: Command word
            created_by: Discord user ID who created the command
            prefix: Command prefix (default: '!')
            response_type: 'text' or 'embed'
            response_text: Text response content
            embed_config: Embed configuration dictionary

        Returns:
            Command ID if successful, None otherwise
        """
        # Serialize embed_config to JSON if provided
        embed_json = json.dumps(embed_config) if embed_config else None

        query = """
            INSERT INTO CustomCommands (
                guild_id, command, prefix, response_type,
                response_text, embed_config, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            str(guild_id),
            command,
            prefix,
            response_type,
            response_text,
            embed_json,
            str(created_by)
        )

        try:
            result = self.execute_write(query, params)
            if result:
                logger.info(f"Created custom command '{prefix}{command}' for guild {guild_id}")
                return result
            return None
        except Exception as e:
            logger.error(f"Error creating custom command for guild {guild_id}: {e}")
            return None

    def get_by_id(self, command_id: int) -> Optional[CustomCommand]:
        """Get custom command by ID"""
        query = "SELECT * FROM CustomCommands WHERE id = %s"
        results, description = self.execute_query(query, (command_id,), return_description=True)

        if results and len(results) > 0 and description:
            columns = [column[0] for column in description]
            entity_dict = dict(zip(columns, results[0]))
            return CustomCommand.from_dict(entity_dict)
        return None

    def get_guild_commands(
        self,
        guild_id: str,
        enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all custom commands for a guild

        Args:
            guild_id: Discord guild ID
            enabled_only: If True, only return enabled commands

        Returns:
            List of command dictionaries
        """
        query = "SELECT * FROM CustomCommands WHERE guild_id = %s"
        params = [str(guild_id)]

        if enabled_only:
            query += " AND is_enabled = TRUE"

        query += " ORDER BY created_at DESC"

        results, description = self.execute_query(query, tuple(params), return_description=True)

        if results and description:
            columns = [column[0] for column in description]
            # Return as dicts for easier API consumption
            return [CustomCommand.from_dict(dict(zip(columns, row))).to_dict() for row in results]
        return []

    def get_command_by_command(
        self,
        guild_id: str,
        command: str,
        prefix: str = '!'
    ) -> Optional[CustomCommand]:
        """Get command by guild ID, command word, and prefix"""
        query = "SELECT * FROM CustomCommands WHERE guild_id = %s AND command = %s AND prefix = %s"
        results, description = self.execute_query(query, (str(guild_id), command, prefix), return_description=True)

        if results and len(results) > 0 and description:
            columns = [column[0] for column in description]
            entity_dict = dict(zip(columns, results[0]))
            return CustomCommand.from_dict(entity_dict)
        return None

    def update_command(
        self,
        command_id: int,
        guild_id: str,
        command: Optional[str] = None,
        prefix: Optional[str] = None,
        response_type: Optional[str] = None,
        response_text: Optional[str] = None,
        embed_config: Optional[Dict[str, Any]] = None,
        is_enabled: Optional[bool] = None
    ) -> bool:
        """
        Update custom command

        Args:
            command_id: Command ID to update
            guild_id: Guild ID (for security check)
            command: New command word (optional)
            prefix: New prefix (optional)
            response_type: New response type (optional)
            response_text: New response text (optional)
            embed_config: New embed config (optional)
            is_enabled: New enabled status (optional)

        Returns:
            True if successful, False otherwise
        """
        updates = []
        params = []

        if command is not None:
            updates.append("command = %s")
            params.append(command)

        if prefix is not None:
            updates.append("prefix = %s")
            params.append(prefix)

        if response_type is not None:
            updates.append("response_type = %s")
            params.append(response_type)

        if response_text is not None:
            updates.append("response_text = %s")
            params.append(response_text)

        if embed_config is not None:
            updates.append("embed_config = %s")
            params.append(json.dumps(embed_config))

        if is_enabled is not None:
            updates.append("is_enabled = %s")
            params.append(is_enabled)

        if not updates:
            logger.warning(f"No updates provided for command {command_id}")
            return False

        updates.append("updated_at = NOW()")
        params.extend([command_id, str(guild_id)])

        query = f"UPDATE CustomCommands SET {', '.join(updates)} WHERE id = %s AND guild_id = %s"

        try:
            result = self.execute_write(query, tuple(params))
            logger.info(f"Updated custom command {command_id}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error updating custom command {command_id}: {e}")
            return False

    def delete_command(self, command_id: int, guild_id: str) -> bool:
        """Delete custom command"""
        query = "DELETE FROM CustomCommands WHERE id = %s AND guild_id = %s"

        try:
            result = self.execute_write(query, (command_id, str(guild_id)))
            logger.info(f"Deleted custom command {command_id}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting custom command {command_id}: {e}")
            return False

    def increment_use_count(self, command_id: int) -> bool:
        """Increment command use count"""
        query = "UPDATE CustomCommands SET use_count = use_count + 1 WHERE id = %s"

        try:
            result = self.execute_write(query, (command_id,))
            return bool(result)
        except Exception as e:
            logger.error(f"Error incrementing use count for command {command_id}: {e}")
            return False

    def count_guild_commands(self, guild_id: str) -> int:
        """Count total commands for a guild"""
        query = "SELECT COUNT(*) as count FROM CustomCommands WHERE guild_id = %s"
        results = self.execute_query(query, (str(guild_id),))

        if results and len(results) > 0:
            result = results[0]
            # Handle both dict and tuple results
            if isinstance(result, dict):
                return result['count'] or 0
            elif isinstance(result, tuple):
                return result[0] or 0
        return 0

    def disable_command(self, command_id: int, guild_id: str) -> bool:
        """Disable a command"""
        return self.update_command(command_id, guild_id, is_enabled=False)

    def enable_command(self, command_id: int, guild_id: str) -> bool:
        """Enable a command"""
        return self.update_command(command_id, guild_id, is_enabled=True)

    def delete_all_guild_commands(self, guild_id: str) -> bool:
        """Delete all commands for a guild (use when downgrading from premium)"""
        query = "DELETE FROM CustomCommands WHERE guild_id = %s"

        try:
            result = self.execute_write(query, (str(guild_id),))
            logger.info(f"Deleted all custom commands for guild {guild_id}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting all commands for guild {guild_id}: {e}")
            return False

    def get_most_used_commands(self, guild_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently used commands for a guild"""
        query = """
            SELECT * FROM CustomCommands
            WHERE guild_id = %s AND is_enabled = TRUE
            ORDER BY use_count DESC
            LIMIT %s
        """
        results, description = self.execute_query(query, (str(guild_id), limit), return_description=True)

        if results and description:
            columns = [column[0] for column in description]
            return [CustomCommand.from_dict(dict(zip(columns, row))).to_dict() for row in results]
        return []
