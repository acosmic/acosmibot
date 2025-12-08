import json
from typing import Dict, Optional
from models.base_models import GuildLevelingRoleSettings, BetterEmbedsSettings
import logging

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Singleton manager class for handling guild settings persistence.

    This class provides a unified API for accessing and updating guild settings
    across the entire application. It should be instantiated once at bot startup
    and injected into cogs that need it.

    Usage:
        # Initialize once at bot startup
        settings_manager = SettingsManager(guild_dao)

        # Use anywhere
        settings = settings_manager.get_guild_settings(guild_id)
        better_embeds = settings_manager.get_better_embeds_settings(guild_id)
        is_enabled = settings_manager.is_instagram_embeds_enabled(guild_id)
    """

    _instance = None
    _initialized = False

    def __new__(cls, guild_dao=None):
        """
        Implement singleton pattern to ensure only one instance exists.

        Args:
            guild_dao: Instance of GuildDao (required on first instantiation)

        Returns:
            The singleton instance of SettingsManager
        """
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, guild_dao=None):
        """
        Initialize the settings manager with a guild DAO.
        Only initializes once due to singleton pattern.

        Args:
            guild_dao: Instance of GuildDao class (required on first initialization)

        Raises:
            ValueError: If guild_dao is None on first initialization
        """
        # Only initialize once
        if self._initialized:
            return

        if guild_dao is None:
            raise ValueError("guild_dao is required for SettingsManager initialization")

        self.guild_dao = guild_dao
        SettingsManager._initialized = True
        logger.info("SettingsManager singleton initialized")

    def get_guild_settings(self, guild_id: str) -> GuildLevelingRoleSettings:
        """
        Get complete guild settings from database.

        Returns default settings if guild not found or settings are invalid.

        Args:
            guild_id: Discord guild ID as string

        Returns:
            GuildLevelingRoleSettings: Guild configuration object with defaults applied
        """
        try:
            guild = self.guild_dao.find_by_id(int(guild_id))

            if guild and guild.settings:
                # Parse JSON settings
                if isinstance(guild.settings, str):
                    settings_dict = json.loads(guild.settings)
                else:
                    settings_dict = guild.settings

                # Extract leveling_role_system section or use empty dict
                lr_settings = settings_dict.get("leveling", {})
                return GuildLevelingRoleSettings(**lr_settings)

            else:
                # Return default settings if guild not found or no settings
                return GuildLevelingRoleSettings()

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing guild settings for {guild_id}: {e}")
            return GuildLevelingRoleSettings()
        except Exception as e:
            logger.error(f"Error getting guild settings for {guild_id}: {e}")
            return GuildLevelingRoleSettings()

    def get_settings_dict(self, guild_id: str) -> Dict:
        """
        Get the complete raw settings dictionary from the database.

        Args:
            guild_id: Discord guild ID as string

        Returns:
            Dict: The complete settings dictionary, or an empty dict if not found.
        """
        try:
            guild = self.guild_dao.find_by_id(int(guild_id))

            if guild and guild.settings:
                # Parse JSON settings
                if isinstance(guild.settings, str):
                    return json.loads(guild.settings)
                # If already a dict (e.g., from an ORM), return it
                return guild.settings

            return {}

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing raw settings dict for {guild_id}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting raw settings dict for {guild_id}: {e}")
            return {}

    def update_guild_settings(self, guild_id: str, settings: GuildLevelingRoleSettings) -> bool:
        """
        Update complete guild settings in database.

        Args:
            guild_id: Discord guild ID as string
            settings: Complete settings object to save

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            guild = self.guild_dao.find_by_id(int(guild_id))

            if guild:
                # Get existing settings or create new dict
                if guild.settings:
                    existing_settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings
                else:
                    existing_settings = {}

                # Update the leveling_role_system section
                existing_settings["leveling_role_system"] = settings.dict()

                # Save back to database
                guild.settings = json.dumps(existing_settings)
                return self.guild_dao.update(guild)

            else:
                # Guild doesn't exist - create new entry
                new_settings = {"leveling_role_system": settings.dict()}
                return self.guild_dao.create_with_settings(int(guild_id), json.dumps(new_settings))

        except Exception as e:
            logger.error(f"Error updating guild settings for {guild_id}: {e}")
            return False

    def get_better_embeds_settings(self, guild_id: str) -> BetterEmbedsSettings:
        """
        Get better embeds configuration for a guild.

        Returns default settings if guild not found or settings are invalid.

        Args:
            guild_id: Discord guild ID as string

        Returns:
            BetterEmbedsSettings: Better embeds configuration object with defaults applied
        """
        try:
            guild = self.guild_dao.find_by_id(int(guild_id))

            if guild and guild.settings:
                # Parse JSON settings
                if isinstance(guild.settings, str):
                    settings_dict = json.loads(guild.settings)
                else:
                    settings_dict = guild.settings

                # Extract better_embeds section or use empty dict
                better_embeds = settings_dict.get("better_embeds", {})
                return BetterEmbedsSettings(**better_embeds)

            else:
                # Return default settings if guild not found
                return BetterEmbedsSettings()

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing better embeds settings for {guild_id}: {e}")
            return BetterEmbedsSettings()
        except Exception as e:
            logger.error(f"Error getting better embeds settings for {guild_id}: {e}")
            return BetterEmbedsSettings()

    def is_instagram_embeds_enabled(self, guild_id: str) -> bool:
        """
        Check if Instagram better embeds are enabled for a guild.

        Args:
            guild_id: Discord guild ID as string

        Returns:
            bool: True if Instagram embeds are enabled, False otherwise
        """
        try:
            better_embeds = self.get_better_embeds_settings(guild_id)
            return better_embeds.enabled and better_embeds.instagram.enabled
        except Exception as e:
            logger.error(f"Error checking Instagram embeds status for {guild_id}: {e}")
            return False

    def update_settings_dict(self, guild_id: str, settings_dict: Dict) -> bool:
        """
        Update guild settings from a dictionary (used by API).

        This method handles the conversion from dict to proper guild settings
        and persists them to the database.

        Args:
            guild_id: Discord guild ID as string
            settings_dict: Dictionary containing settings to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Call the underlying DAO method directly for dict-based updates
            return self.guild_dao.update_guild_settings(int(guild_id), settings_dict)
        except Exception as e:
            logger.error(f"Error updating settings dict for {guild_id}: {e}")
            return False

    @classmethod
    def reset_singleton(cls):
        """
        Reset the singleton instance (useful for testing).

        WARNING: Only call this in test environments.
        """
        cls._instance = None
        cls._initialized = False
        logger.warning("SettingsManager singleton has been reset")

    @classmethod
    def get_instance(cls) -> 'SettingsManager':
        """
        Get the singleton instance without initializing it.
        Raises ValueError if not yet initialized.

        Returns:
            The singleton instance of SettingsManager

        Raises:
            ValueError: If SettingsManager hasn't been initialized yet
        """
        if cls._instance is None or not cls._initialized:
            raise ValueError(
                "SettingsManager not yet initialized. "
                "Call SettingsManager(guild_dao) to initialize it first."
            )
        return cls._instance
