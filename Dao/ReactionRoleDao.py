#! /usr/bin/python3.10
from typing import Optional, List
from database import Database
from Dao.BaseDao import BaseDao
from Entities.ReactionRole import ReactionRole
from datetime import datetime
import json


class ReactionRoleDao(BaseDao[ReactionRole]):
    """
    Data Access Object for ReactionRole entities.
    Provides methods to interact with the ReactionRoles table in the database.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the ReactionRoleDao with connection parameters.

        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(ReactionRole, "ReactionRoles", db)

    def create_table(self) -> bool:
        """
        Create the ReactionRoles table if it doesn't exist.

        Returns:
            bool: True if successful, False otherwise
        """
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS ReactionRoles (
                id INT PRIMARY KEY AUTO_INCREMENT,
                guild_id BIGINT NOT NULL,
                message_id BIGINT NOT NULL UNIQUE,
                channel_id BIGINT NOT NULL,
                interaction_type ENUM('emoji', 'button', 'dropdown') NOT NULL,
                text_content LONGTEXT,
                embed_config JSON,
                allow_removal BOOLEAN DEFAULT true,
                emoji_role_mappings JSON,
                button_configs JSON,
                dropdown_config JSON,
                enabled BOOLEAN DEFAULT true,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES Guilds(id),
                INDEX (guild_id),
                INDEX (message_id)
            );
        """

        try:
            self.create_table_if_not_exists(create_table_sql)
            return True
        except Exception as e:
            self.logger.error(f"Error creating ReactionRoles table: {e}")
            return False

    def create_reaction_role(self, reaction_role: ReactionRole) -> bool:
        """
        Create a new reaction role configuration.

        Args:
            reaction_role (ReactionRole): ReactionRole to add

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            INSERT INTO ReactionRoles (
                guild_id, message_id, channel_id, interaction_type, text_content,
                embed_config, allow_removal, emoji_role_mappings, button_configs,
                dropdown_config, enabled, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        now = datetime.now()

        values = (
            reaction_role.guild_id,
            reaction_role.message_id,
            reaction_role.channel_id,
            reaction_role.interaction_type,
            reaction_role.text_content,
            reaction_role.embed_config,
            reaction_role.allow_removal,
            reaction_role.emoji_role_mappings,
            reaction_role.button_configs,
            reaction_role.dropdown_config,
            reaction_role.enabled,
            now,
            now
        )

        try:
            return self.execute_query(sql, values, commit=True)
        except Exception as e:
            self.logger.error(f"Error creating reaction role: {e}")
            return False

    def get_reaction_role_by_message_id(self, message_id: int) -> Optional[ReactionRole]:
        """
        Get a reaction role configuration by message ID.

        Args:
            message_id (int): Discord message ID

        Returns:
            Optional[ReactionRole]: ReactionRole if found, None otherwise
        """
        sql = """
            SELECT id, guild_id, message_id, channel_id, interaction_type, text_content,
                   embed_config, allow_removal, emoji_role_mappings, button_configs,
                   dropdown_config, enabled, created_at, updated_at
            FROM ReactionRoles
            WHERE message_id = %s
        """

        try:
            result = self.execute_query(sql, (message_id,))

            if result and len(result) > 0:
                return self._row_to_entity(result[0])

            return None

        except Exception as e:
            self.logger.error(f"Error getting reaction role by message_id {message_id}: {e}")
            return None

    def get_all_by_guild(self, guild_id: int) -> List[ReactionRole]:
        """
        Get all reaction role configurations for a guild.

        Args:
            guild_id (int): Discord guild ID

        Returns:
            List[ReactionRole]: List of ReactionRole objects
        """
        sql = """
            SELECT id, guild_id, message_id, channel_id, interaction_type, text_content,
                   embed_config, allow_removal, emoji_role_mappings, button_configs,
                   dropdown_config, enabled, created_at, updated_at
            FROM ReactionRoles
            WHERE guild_id = %s AND enabled = true
            ORDER BY created_at DESC
        """

        try:
            results = self.execute_query(sql, (guild_id,))

            if results:
                return [self._row_to_entity(row) for row in results]

            return []

        except Exception as e:
            self.logger.error(f"Error getting reaction roles for guild {guild_id}: {e}")
            return []

    def get_by_id(self, reaction_role_id: int) -> Optional[ReactionRole]:
        """
        Get a reaction role by database ID.

        Args:
            reaction_role_id (int): Database ID

        Returns:
            Optional[ReactionRole]: ReactionRole if found, None otherwise
        """
        sql = """
            SELECT id, guild_id, message_id, channel_id, interaction_type, text_content,
                   embed_config, allow_removal, emoji_role_mappings, button_configs,
                   dropdown_config, enabled, created_at, updated_at
            FROM ReactionRoles
            WHERE id = %s
        """

        try:
            result = self.execute_query(sql, (reaction_role_id,))

            if result and len(result) > 0:
                return self._row_to_entity(result[0])

            return None

        except Exception as e:
            self.logger.error(f"Error getting reaction role by id {reaction_role_id}: {e}")
            return None

    def update_reaction_role(self, reaction_role: ReactionRole) -> bool:
        """
        Update an existing reaction role configuration.

        Args:
            reaction_role (ReactionRole): ReactionRole to update

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            UPDATE ReactionRoles
            SET guild_id = %s, channel_id = %s, interaction_type = %s, text_content = %s,
                embed_config = %s, allow_removal = %s, emoji_role_mappings = %s,
                button_configs = %s, dropdown_config = %s, enabled = %s, updated_at = %s
            WHERE message_id = %s
        """

        now = datetime.now()

        values = (
            reaction_role.guild_id,
            reaction_role.channel_id,
            reaction_role.interaction_type,
            reaction_role.text_content,
            reaction_role.embed_config,
            reaction_role.allow_removal,
            reaction_role.emoji_role_mappings,
            reaction_role.button_configs,
            reaction_role.dropdown_config,
            reaction_role.enabled,
            now,
            reaction_role.message_id
        )

        try:
            return self.execute_query(sql, values, commit=True)
        except Exception as e:
            self.logger.error(f"Error updating reaction role: {e}")
            return False

    def delete_reaction_role(self, message_id: int) -> bool:
        """
        Delete a reaction role configuration by message ID.

        Args:
            message_id (int): Discord message ID

        Returns:
            bool: True if successful, False otherwise
        """
        sql = "DELETE FROM ReactionRoles WHERE message_id = %s"

        try:
            return self.execute_query(sql, (message_id,), commit=True)
        except Exception as e:
            self.logger.error(f"Error deleting reaction role with message_id {message_id}: {e}")
            return False

    def _row_to_entity(self, row: tuple) -> ReactionRole:
        """
        Convert a database row to a ReactionRole entity.

        Args:
            row (tuple): Database row

        Returns:
            ReactionRole: ReactionRole entity
        """
        return ReactionRole(
            id=row[0],
            guild_id=row[1],
            message_id=row[2],
            channel_id=row[3],
            interaction_type=row[4],
            text_content=row[5],
            embed_config=row[6],
            allow_removal=row[7],
            emoji_role_mappings=row[8],
            button_configs=row[9],
            dropdown_config=row[10],
            enabled=row[11],
            created_at=row[12],
            updated_at=row[13]
        )
