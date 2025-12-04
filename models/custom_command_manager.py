#! /usr/bin/python3.10
"""
Custom Command Manager

Business logic layer for managing and executing custom commands.
Handles caching, validation, and embed construction.
"""
import re
from typing import Optional, List, Dict, Any
import discord
from Dao.CustomCommandDao import CustomCommandDao
from Entities.CustomCommand import CustomCommand
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class CustomCommandManager:
    """Manager for custom command operations with caching"""

    def __init__(self):
        """Initialize the manager with empty cache"""
        self._cache: Dict[str, List[CustomCommand]] = {}
        logger.info("CustomCommandManager initialized")

    def get_guild_commands(
        self,
        guild_id: int,
        enabled_only: bool = True,
        use_cache: bool = False
    ) -> List[CustomCommand]:
        """
        Get all custom commands for a guild

        Args:
            guild_id: Discord guild ID
            enabled_only: If True, only return enabled commands
            use_cache: If True, use cached data if available (default: False for real-time updates)

        Returns:
            List of CustomCommand entities
        """
        guild_key = str(guild_id)

        # Check cache first
        if use_cache and guild_key in self._cache:
            commands = self._cache[guild_key]
            if enabled_only:
                return [cmd for cmd in commands if cmd.is_enabled]
            return commands

        # Fetch from database
        try:
            with CustomCommandDao() as dao:
                command_dicts = dao.get_guild_commands(
                    guild_id=str(guild_id),
                    enabled_only=False  # Get all, filter later if needed
                )

                commands = [CustomCommand.from_dict(cmd) for cmd in command_dicts]

                # Update cache
                self._cache[guild_key] = commands

                logger.debug(f"Loaded {len(commands)} commands for guild {guild_id}")

                if enabled_only:
                    return [cmd for cmd in commands if cmd.is_enabled]
                return commands

        except Exception as e:
            logger.error(f"Error fetching commands for guild {guild_id}: {e}")
            return []

    def get_command(
        self,
        guild_id: int,
        command: str,
        prefix: str = '!'
    ) -> Optional[CustomCommand]:
        """
        Get a specific custom command

        Args:
            guild_id: Discord guild ID
            command: Command word (without prefix)
            prefix: Command prefix

        Returns:
            CustomCommand entity or None if not found
        """
        try:
            with CustomCommandDao() as dao:
                return dao.get_command_by_command(
                    guild_id=str(guild_id),
                    command=command,
                    prefix=prefix
                )
        except Exception as e:
            logger.error(f"Error fetching command '{prefix}{command}' for guild {guild_id}: {e}")
            return None

    def refresh_cache(self, guild_id: int):
        """
        Refresh cached commands for a guild

        Args:
            guild_id: Discord guild ID
        """
        guild_key = str(guild_id)

        try:
            with CustomCommandDao() as dao:
                command_dicts = dao.get_guild_commands(
                    guild_id=str(guild_id),
                    enabled_only=False
                )
                commands = [CustomCommand.from_dict(cmd) for cmd in command_dicts]
                self._cache[guild_key] = commands
                logger.info(f"Refreshed cache for guild {guild_id}: {len(commands)} commands")

        except Exception as e:
            logger.error(f"Error refreshing cache for guild {guild_id}: {e}")

    def clear_cache(self, guild_id: Optional[int] = None):
        """
        Clear command cache

        Args:
            guild_id: If provided, clear only this guild. Otherwise clear all.
        """
        if guild_id:
            guild_key = str(guild_id)
            if guild_key in self._cache:
                del self._cache[guild_key]
                logger.debug(f"Cleared cache for guild {guild_id}")
        else:
            self._cache.clear()
            logger.debug("Cleared all command cache")

    @staticmethod
    def build_embed_from_config(embed_config: Dict[str, Any]) -> discord.Embed:
        """
        Build a Discord embed from configuration dictionary

        Args:
            embed_config: Dictionary with embed configuration

        Returns:
            discord.Embed object

        Raises:
            ValueError: If embed config is invalid
        """
        try:
            # Parse color (hex string to int)
            color_str = embed_config.get('color', '#5865F2')
            if isinstance(color_str, str):
                color = int(color_str.lstrip('#'), 16)
            else:
                color = color_str

            # Create embed
            embed = discord.Embed(
                title=embed_config.get('title'),
                description=embed_config.get('description'),
                color=color
            )

            # Add thumbnail
            if embed_config.get('thumbnail'):
                embed.set_thumbnail(url=embed_config['thumbnail'])

            # Add image
            if embed_config.get('image'):
                embed.set_image(url=embed_config['image'])

            # Add footer
            if embed_config.get('footer'):
                embed.set_footer(text=embed_config['footer'])

            # Add author
            if embed_config.get('author_name'):
                embed.set_author(name=embed_config['author_name'])

            # Add fields
            for field in embed_config.get('fields', []):
                if 'name' in field and 'value' in field:
                    embed.add_field(
                        name=field['name'],
                        value=field['value'],
                        inline=field.get('inline', False)
                    )

            return embed

        except Exception as e:
            logger.error(f"Error building embed from config: {e}")
            raise ValueError(f"Invalid embed configuration: {e}")

    @staticmethod
    def validate_command_name(command: str) -> tuple[bool, str]:
        """
        Validate command name format

        Args:
            command: Command word to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not command:
            return False, "Command name cannot be empty"

        if len(command) > 100:
            return False, "Command name must be 100 characters or less"

        # Allow alphanumeric, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', command):
            return False, "Command name can only contain letters, numbers, hyphens, and underscores"

        # Reserved command names (Discord slash commands, bot commands)
        reserved = {
            'help', 'info', 'ping', 'stats', 'settings',
            'config', 'setup', 'admin', 'mod', 'moderator'
        }
        if command.lower() in reserved:
            return False, f"Command name '{command}' is reserved"

        return True, ""

    @staticmethod
    def validate_embed_config(embed_config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate embed configuration

        Args:
            embed_config: Embed configuration dictionary

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not embed_config:
            return False, "Embed configuration cannot be empty"

        # Must have at least title or description
        if not embed_config.get('title') and not embed_config.get('description'):
            return False, "Embed must have at least a title or description"

        # Validate color format
        if 'color' in embed_config:
            color = embed_config['color']
            if isinstance(color, str):
                if not re.match(r'^#?[0-9A-Fa-f]{6}$', color):
                    return False, "Color must be a valid hex code (e.g., #5865F2)"

        # Validate fields
        if 'fields' in embed_config:
            if not isinstance(embed_config['fields'], list):
                return False, "Fields must be a list"

            for i, field in enumerate(embed_config['fields']):
                if not isinstance(field, dict):
                    return False, f"Field {i+1} must be an object"
                if 'name' not in field or 'value' not in field:
                    return False, f"Field {i+1} must have 'name' and 'value'"

        return True, ""

    def increment_use_count(self, command_id: int):
        """
        Increment the use count for a command

        Args:
            command_id: Command ID
        """
        try:
            with CustomCommandDao() as dao:
                dao.increment_use_count(command_id)
        except Exception as e:
            logger.error(f"Error incrementing use count for command {command_id}: {e}")
