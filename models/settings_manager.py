import json
from typing import Dict, List, Optional
from models.base_models import GuildLevelingRoleSettings, RoleCacheEntry
from models.api_models import UpdateLevelingSettingsRequest, UpdateRoleSettingsRequest


class SettingsManager:
    """Manager class for handling guild models persistence"""

    def __init__(self, guild_dao):
        """
        Initialize the models manager with a guild DAO

        Args:
            guild_dao: Instance of your GuildDao class
        """
        self.guild_dao = guild_dao

    def get_guild_settings(self, guild_id: str) -> GuildLevelingRoleSettings:
        """
        Get guild models from database

        Args:
            guild_id: Discord guild ID as string

        Returns:
            GuildLevelingRoleSettings: Guild configuration object
        """
        try:
            guild = self.guild_dao.find_by_id(int(guild_id))

            if guild and guild.settings:
                # Parse JSON models
                if isinstance(guild.settings, str):
                    settings_dict = json.loads(guild.settings)
                else:
                    settings_dict = guild.settings

                # Extract leveling_role_system section or use empty dict
                lr_settings = settings_dict.get("leveling_role_system", {})
                return GuildLevelingRoleSettings(**lr_settings)

            else:
                # Return default models if guild not found or no models
                return GuildLevelingRoleSettings()

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing guild models for {guild_id}: {e}")
            return GuildLevelingRoleSettings()
        except Exception as e:
            print(f"Error getting guild models for {guild_id}: {e}")
            return GuildLevelingRoleSettings()

    def update_guild_settings(self, guild_id: str, settings: GuildLevelingRoleSettings) -> bool:
        """
        Update complete guild models in database

        Args:
            guild_id: Discord guild ID as string
            settings: Complete models object to save

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            guild = self.guild_dao.find_by_id(int(guild_id))

            if guild:
                # Get existing models or create new dict
                if guild.settings:
                    existing_settings = json.loads(guild.settings) if isinstance(guild.settings,
                                                                                 str) else guild.settings
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
            print(f"Error updating guild models for {guild_id}: {e}")
            return False

    def update_leveling_settings(self, guild_id: str, updates: UpdateLevelingSettingsRequest) -> bool:
        """
        Update only leveling models (partial update)

        Args:
            guild_id: Discord guild ID as string
            updates: Partial leveling models to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current models
            settings = self.get_guild_settings(guild_id)

            # Apply updates (only fields that were provided)
            update_data = updates.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(settings.leveling, field):
                    setattr(settings.leveling, field, value)

            # Save updated models
            return self.update_guild_settings(guild_id, settings)

        except Exception as e:
            print(f"Error updating leveling models for {guild_id}: {e}")
            return False

    def update_role_settings(self, guild_id: str, updates: UpdateRoleSettingsRequest) -> bool:
        """
        Update only role models (partial update)

        Args:
            guild_id: Discord guild ID as string
            updates: Partial role models to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current models
            settings = self.get_guild_settings(guild_id)

            # Apply updates (only fields that were provided)
            update_data = updates.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(settings.roles, field):
                    setattr(settings.roles, field, value)

            # Save updated models
            return self.update_guild_settings(guild_id, settings)

        except Exception as e:
            print(f"Error updating role models for {guild_id}: {e}")
            return False

    def update_role_mapping(self, guild_id: str, level: int, role_ids: List[str],
                            role_cache: Optional[Dict[str, RoleCacheEntry]] = None) -> bool:
        """
        Update role mapping for a specific level

        Args:
            guild_id: Discord guild ID as string
            level: Level number
            role_ids: List of Discord role IDs to assign at this level
            role_cache: Optional role cache entries to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current models
            settings = self.get_guild_settings(guild_id)

            # Update role mappings
            settings.roles.set_roles_for_level(level, role_ids)

            # Update role cache if provided
            if role_cache:
                for role_id, cache_entry in role_cache.items():
                    settings.roles.role_cache[role_id] = cache_entry

            # Enable role system if roles are being assigned
            if role_ids:
                settings.roles.enabled = True

            # Save updated models
            return self.update_guild_settings(guild_id, settings)

        except Exception as e:
            print(f"Error updating role mapping for {guild_id}: {e}")
            return False

    def delete_role_mapping(self, guild_id: str, level: int) -> bool:
        """
        Delete role mapping for a specific level

        Args:
            guild_id: Discord guild ID as string
            level: Level number to remove mappings for

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current models
            settings = self.get_guild_settings(guild_id)

            # Remove the mapping (set_roles_for_level with empty list removes it)
            settings.roles.set_roles_for_level(level, [])

            # Save updated models
            return self.update_guild_settings(guild_id, settings)

        except Exception as e:
            print(f"Error deleting role mapping for {guild_id}: {e}")
            return False

    def add_role_to_level(self, guild_id: str, level: int, role_id: str,
                          role_cache_entry: Optional[RoleCacheEntry] = None) -> bool:
        """
        Add a single role to a level (convenience method)

        Args:
            guild_id: Discord guild ID as string
            level: Level number
            role_id: Discord role ID to add
            role_cache_entry: Optional cache entry for the role

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current models
            settings = self.get_guild_settings(guild_id)

            # Get existing roles for this level
            existing_roles = settings.roles.get_roles_for_level(level)

            # Add role if not already present
            if role_id not in existing_roles:
                existing_roles.append(role_id)

                # Update role cache if provided
                role_cache = {}
                if role_cache_entry:
                    role_cache[role_id] = role_cache_entry

                return self.update_role_mapping(guild_id, level, existing_roles, role_cache)

            return True  # Role already exists, consider it successful

        except Exception as e:
            print(f"Error adding role to level for {guild_id}: {e}")
            return False

    def remove_role_from_level(self, guild_id: str, level: int, role_id: str) -> bool:
        """
        Remove a single role from a level (convenience method)

        Args:
            guild_id: Discord guild ID as string
            level: Level number
            role_id: Discord role ID to remove

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current models
            settings = self.get_guild_settings(guild_id)

            # Get existing roles for this level
            existing_roles = settings.roles.get_roles_for_level(level)

            # Remove role if present
            if role_id in existing_roles:
                existing_roles.remove(role_id)
                return self.update_role_mapping(guild_id, level, existing_roles)

            return True  # Role wasn't there anyway, consider it successful

        except Exception as e:
            print(f"Error removing role from level for {guild_id}: {e}")
            return False

    def get_role_configuration(self, guild_id: str) -> Dict[int, List[Dict[str, str]]]:
        """
        Get human-readable role configuration for a guild

        Args:
            guild_id: Discord guild ID as string

        Returns:
            Dict mapping level -> list of role info dicts with id and name
        """
        try:
            settings = self.get_guild_settings(guild_id)
            result = {}

            for level_str, role_ids in settings.roles.role_mappings.items():
                level = int(level_str)
                result[level] = []

                for role_id in role_ids:
                    # Get role info from cache
                    role_info = settings.roles.role_cache.get(role_id)
                    if role_info:
                        result[level].append({
                            "id": role_id,
                            "name": role_info.name,
                            "color": role_info.color
                        })
                    else:
                        result[level].append({
                            "id": role_id,
                            "name": "Unknown Role",
                            "color": "#99AAB5"
                        })

            return result

        except Exception as e:
            print(f"Error getting role configuration for {guild_id}: {e}")
            return {}

    def is_leveling_enabled(self, guild_id: str) -> bool:
        """Check if leveling system is enabled for a guild"""
        settings = self.get_guild_settings(guild_id)
        return settings.leveling.enabled

    def is_role_system_enabled(self, guild_id: str) -> bool:
        """Check if role system is enabled for a guild"""
        settings = self.get_guild_settings(guild_id)
        return settings.roles.enabled

    def get_exp_per_message(self, guild_id: str) -> int:
        """Get XP per message setting for a guild"""
        settings = self.get_guild_settings(guild_id)
        return settings.leveling.exp_per_message

    def get_level_up_channel(self, guild_id: str) -> Optional[str]:
        """Get level up announcement channel ID if announcements are enabled"""
        settings = self.get_guild_settings(guild_id)
        if settings.leveling.level_up_announcements:
            return settings.leveling.announcement_channel_id
        return None