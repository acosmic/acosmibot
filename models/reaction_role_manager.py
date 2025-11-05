#! /usr/bin/python3.10
import json
import logging
from typing import Dict, List, Optional, Any
from Entities.ReactionRole import ReactionRole
from Dao.ReactionRoleDao import ReactionRoleDao

logger = logging.getLogger(__name__)


class ReactionRoleManager:
    """Manager class for handling reaction role configurations"""

    def __init__(self, reaction_role_dao: ReactionRoleDao):
        """
        Initialize the manager with a reaction role DAO

        Args:
            reaction_role_dao: Instance of ReactionRoleDao
        """
        self.dao = reaction_role_dao

    def get_reaction_config(self, message_id: int) -> Optional[Dict[str, Any]]:
        """
        Get complete reaction role configuration for a message

        Args:
            message_id: Discord message ID

        Returns:
            Dict with parsed configuration or None if not found
        """
        try:
            reaction_role = self.dao.get_reaction_role_by_message_id(message_id)

            if not reaction_role:
                return None

            # Parse JSON fields
            config = {
                "id": reaction_role.id,
                "guild_id": reaction_role.guild_id,
                "message_id": reaction_role.message_id,
                "channel_id": reaction_role.channel_id,
                "interaction_type": reaction_role.interaction_type,
                "text_content": reaction_role.text_content,
                "embed_config": self._parse_json(reaction_role.embed_config),
                "allow_removal": reaction_role.allow_removal,
                "enabled": reaction_role.enabled,
                "created_at": reaction_role.created_at,
                "updated_at": reaction_role.updated_at
            }

            # Parse type-specific configs
            if reaction_role.interaction_type == "emoji":
                config["emoji_role_mappings"] = self._parse_json(reaction_role.emoji_role_mappings) or {}
            elif reaction_role.interaction_type == "button":
                config["button_configs"] = self._parse_json(reaction_role.button_configs) or []
            elif reaction_role.interaction_type == "dropdown":
                config["dropdown_config"] = self._parse_json(reaction_role.dropdown_config) or {}

            return config

        except Exception as e:
            logger.error(f"Error getting reaction config for message {message_id}: {e}")
            return None

    def get_all_for_guild(self, guild_id: int) -> List[Dict[str, Any]]:
        """
        Get all reaction role configurations for a guild

        Args:
            guild_id: Discord guild ID

        Returns:
            List of parsed reaction role configurations
        """
        try:
            reaction_roles = self.dao.get_all_by_guild(guild_id)
            configs = []

            for rr in reaction_roles:
                config = self.get_reaction_config(rr.message_id)
                if config:
                    configs.append(config)

            return configs

        except Exception as e:
            logger.error(f"Error getting reaction configs for guild {guild_id}: {e}")
            return []

    def create_reaction_role(
            self,
            guild_id: int,
            message_id: int,
            channel_id: int,
            interaction_type: str,
            text_content: Optional[str] = None,
            embed_config: Optional[Dict[str, Any]] = None,
            allow_removal: bool = True,
            emoji_role_mappings: Optional[Dict[str, List[int]]] = None,
            button_configs: Optional[List[Dict[str, Any]]] = None,
            dropdown_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new reaction role configuration

        Args:
            guild_id: Discord guild ID
            message_id: Discord message ID
            channel_id: Discord channel ID
            interaction_type: Type of interaction (emoji, button, dropdown)
            text_content: Optional text content for the message
            embed_config: Optional embed configuration
            allow_removal: Whether users can remove roles
            emoji_role_mappings: Emoji to role IDs mapping (for emoji type)
            button_configs: Button configurations (for button type)
            dropdown_config: Dropdown configuration (for dropdown type)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate input
            if not text_content and not embed_config:
                logger.error("Either text_content or embed_config must be provided")
                return False

            if interaction_type not in ["emoji", "button", "dropdown"]:
                logger.error(f"Invalid interaction_type: {interaction_type}")
                return False

            reaction_role = ReactionRole(
                guild_id=guild_id,
                message_id=message_id,
                channel_id=channel_id,
                interaction_type=interaction_type,
                text_content=text_content,
                embed_config=json.dumps(embed_config) if embed_config else None,
                allow_removal=allow_removal,
                emoji_role_mappings=json.dumps(emoji_role_mappings) if emoji_role_mappings else None,
                button_configs=json.dumps(button_configs) if button_configs else None,
                dropdown_config=json.dumps(dropdown_config) if dropdown_config else None,
                enabled=True
            )

            return self.dao.create_reaction_role(reaction_role)

        except Exception as e:
            logger.error(f"Error creating reaction role: {e}")
            return False

    def update_reaction_role(
            self,
            message_id: int,
            guild_id: Optional[int] = None,
            channel_id: Optional[int] = None,
            interaction_type: Optional[str] = None,
            text_content: Optional[str] = None,
            embed_config: Optional[Dict[str, Any]] = None,
            allow_removal: Optional[bool] = None,
            emoji_role_mappings: Optional[Dict[str, List[int]]] = None,
            button_configs: Optional[List[Dict[str, Any]]] = None,
            dropdown_config: Optional[Dict[str, Any]] = None,
            enabled: Optional[bool] = None
    ) -> bool:
        """
        Update an existing reaction role configuration

        Args:
            message_id: Discord message ID to update
            guild_id: Optional guild ID
            channel_id: Optional channel ID
            interaction_type: Optional interaction type
            text_content: Optional text content
            embed_config: Optional embed config
            allow_removal: Optional removal setting
            emoji_role_mappings: Optional emoji mappings
            button_configs: Optional button configs
            dropdown_config: Optional dropdown config
            enabled: Optional enabled flag

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get existing config
            existing = self.dao.get_reaction_role_by_message_id(message_id)
            if not existing:
                logger.error(f"Reaction role with message_id {message_id} not found")
                return False

            # Update fields with provided values or keep existing
            updated = ReactionRole(
                id=existing.id,
                guild_id=guild_id or existing.guild_id,
                message_id=message_id,
                channel_id=channel_id or existing.channel_id,
                interaction_type=interaction_type or existing.interaction_type,
                text_content=text_content if text_content is not None else existing.text_content,
                embed_config=json.dumps(embed_config) if embed_config else existing.embed_config,
                allow_removal=allow_removal if allow_removal is not None else existing.allow_removal,
                emoji_role_mappings=json.dumps(emoji_role_mappings) if emoji_role_mappings else existing.emoji_role_mappings,
                button_configs=json.dumps(button_configs) if button_configs else existing.button_configs,
                dropdown_config=json.dumps(dropdown_config) if dropdown_config else existing.dropdown_config,
                enabled=enabled if enabled is not None else existing.enabled
            )

            return self.dao.update_reaction_role(updated)

        except Exception as e:
            logger.error(f"Error updating reaction role: {e}")
            return False

    def delete_reaction_role(self, message_id: int) -> bool:
        """
        Delete a reaction role configuration

        Args:
            message_id: Discord message ID to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return self.dao.delete_reaction_role(message_id)
        except Exception as e:
            logger.error(f"Error deleting reaction role: {e}")
            return False

    def get_emoji_role_mapping(self, message_id: int) -> Optional[Dict[str, List[int]]]:
        """
        Get emoji to role ID mapping for a message

        Args:
            message_id: Discord message ID

        Returns:
            Dict mapping emoji to list of role IDs, or None if not found
        """
        config = self.get_reaction_config(message_id)
        if config and config.get("interaction_type") == "emoji":
            return config.get("emoji_role_mappings", {})
        return None

    def get_button_configs(self, message_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get button configurations for a message

        Args:
            message_id: Discord message ID

        Returns:
            List of button configs, or None if not found
        """
        config = self.get_reaction_config(message_id)
        if config and config.get("interaction_type") == "button":
            return config.get("button_configs", [])
        return None

    def get_dropdown_config(self, message_id: int) -> Optional[Dict[str, Any]]:
        """
        Get dropdown configuration for a message

        Args:
            message_id: Discord message ID

        Returns:
            Dropdown config dict, or None if not found
        """
        config = self.get_reaction_config(message_id)
        if config and config.get("interaction_type") == "dropdown":
            return config.get("dropdown_config", {})
        return None

    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a reaction role configuration

        Args:
            config: Configuration dict to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check required fields
            required = ["interaction_type", "guild_id", "message_id", "channel_id"]
            for field in required:
                if field not in config:
                    return False, f"Missing required field: {field}"

            # Check interaction type
            if config["interaction_type"] not in ["emoji", "button", "dropdown"]:
                return False, f"Invalid interaction_type: {config['interaction_type']}"

            # Check at least one of text or embed
            if not config.get("text_content") and not config.get("embed_config"):
                return False, "Either text_content or embed_config must be provided"

            # Type-specific validations
            if config["interaction_type"] == "emoji":
                if not config.get("emoji_role_mappings"):
                    return False, "emoji_role_mappings required for emoji type"
                if not isinstance(config["emoji_role_mappings"], dict):
                    return False, "emoji_role_mappings must be a dictionary"

            elif config["interaction_type"] == "button":
                if not config.get("button_configs"):
                    return False, "button_configs required for button type"
                if not isinstance(config["button_configs"], list) or len(config["button_configs"]) == 0:
                    return False, "button_configs must be a non-empty list"

            elif config["interaction_type"] == "dropdown":
                if not config.get("dropdown_config"):
                    return False, "dropdown_config required for dropdown type"
                if not isinstance(config["dropdown_config"], dict):
                    return False, "dropdown_config must be a dictionary"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def _parse_json(json_str: Optional[str]) -> Optional[Any]:
        """
        Safely parse a JSON string

        Args:
            json_str: JSON string to parse

        Returns:
            Parsed object or None if empty/invalid
        """
        if not json_str:
            return None

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON: {e}")
            return None
