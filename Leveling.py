import discord
from discord.ext import commands
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Dao.GuildDao import GuildDao
from datetime import datetime, timedelta
from logger import AppLogger
import json
import math

logger = AppLogger(__name__).get_logger()


class LevelingSystem:
    def __init__(self, bot):
        self.bot = bot
        self.user_cooldowns = {}  # Track user cooldowns per guild

        # Default configuration
        self.default_config = {
            "enabled": True,  # Deprecated - always true (stats always tracked)
            "exp_per_message": 10,
            "exp_cooldown_seconds": 3,
            "level_up_announcements": True,
            "announcement_channel_id": None,
            "streak_multiplier": 0.05,  # 5% bonus per streak day
            "max_streak_bonus": 20,  # Maximum streak days for bonus calculation
            "daily_bonus": 1000,  # Daily reward bonus amount
            "daily_announcements_enabled": False,  # Enable daily reward announcements
            "daily_announcement_channel_id": None  # Channel for daily reward announcements
        }

    def get_leveling_config(self, guild_id):
        """Get leveling configuration from guild settings"""
        try:
            guild_dao = GuildDao()
            try:
                guild = guild_dao.get_guild(guild_id)

                if not guild or not guild.settings:
                    return self.default_config

                # Parse settings JSON
                settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings

                # Get leveling settings or return default
                leveling_settings = settings.get("leveling", {})

                # Merge with defaults
                config = self.default_config.copy()
                config.update(leveling_settings)

                return config
            finally:
                guild_dao.close()

        except Exception as e:
            logger.error(f"Error getting leveling config: {e}")
            return self.default_config

    def calculate_level_from_exp(self, exp):
        """Calculate level from experience points using standard formula"""
        if exp < 0:
            return 0
        # Using formula: level = floor(sqrt(exp / 100))
        # This means: level 1 = 100 exp, level 2 = 400 exp, level 3 = 900 exp, etc.
        return math.floor(math.sqrt(exp / 100))

    def calculate_exp_for_level(self, level):
        """Calculate experience needed for a specific level"""
        return level * level * 100

    def calc_exp_required(self, level):
        """Legacy method name for compatibility with rank cog"""
        return self.calculate_exp_for_level(level)

    def calc_level(self, exp):
        """Legacy method name for compatibility with rank cog"""
        return self.calculate_level_from_exp(exp)

    def is_user_on_cooldown(self, user_id, guild_id, cooldown_seconds):
        """Check if user is on experience cooldown"""
        now = datetime.now()

        # Auto-cleanup: remove expired cooldown entries to prevent memory leak
        expired_keys = [
            key for key, timestamp in self.user_cooldowns.items()
            if (now - timestamp).total_seconds() > cooldown_seconds
        ]
        for key in expired_keys:
            del self.user_cooldowns[key]

        # Check current user's cooldown
        cooldown_key = f"{guild_id}_{user_id}"

        if cooldown_key not in self.user_cooldowns:
            return False

        last_exp_time = self.user_cooldowns[cooldown_key]
        time_since_last = (now - last_exp_time).total_seconds()

        return time_since_last < cooldown_seconds

    def set_user_cooldown(self, user_id, guild_id):
        """Set user on experience cooldown"""
        cooldown_key = f"{guild_id}_{user_id}"
        self.user_cooldowns[cooldown_key] = datetime.now()

    async def process_message_exp(self, message):
        """
        Process message counting and experience gain from a message.

        Message counting happens ALWAYS (independent of leveling toggle).
        Exp/leveling only processes when leveling is enabled.
        """
        # Skip bots
        if message.author.bot:
            return

        # Skip DMs
        if not hasattr(message, 'guild') or not message.guild:
            return

        guild_id = message.guild.id
        user_id = message.author.id

        # Get leveling configuration
        config = self.get_leveling_config(guild_id)

        guild_user_dao = None
        user_dao = None
        try:
            # Get DAOs
            guild_user_dao = GuildUserDao()
            user_dao = UserDao()

            # Get or create guild user
            guild_user = guild_user_dao.get_guild_user(user_id, guild_id)
            if not guild_user:
                # Initialize new guild user if needed
                return

            # Get or create global user
            global_user = user_dao.get_user(user_id)
            if not global_user:
                return

            # === ALWAYS UPDATE MESSAGE COUNTS AND ACTIVITY ===
            guild_user.messages_sent += 1
            guild_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            global_user.total_messages += 1
            global_user.last_seen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # === ALWAYS PROCESS EXP AND LEVELS (stats always tracked) ===
            # Note: leveling.enabled is deprecated - stats are always tracked now
            # Announcements and roles are controlled by separate toggles

            # Check cooldown (but still save message count above even if on cooldown)
            if self.is_user_on_cooldown(user_id, guild_id, config["exp_cooldown_seconds"]):
                # Save the message count even though exp is not awarded due to cooldown
                guild_user_dao.update_guild_user(guild_user)
                user_dao.update_user(global_user)
                return

            # Calculate old level
            old_level = self.calculate_level_from_exp(guild_user.exp)

            # Calculate experience with streak multiplier
            base_exp = config["exp_per_message"]

            # Apply streak multiplier (similar to current system)
            streak = min(guild_user.streak, config["max_streak_bonus"])  # Cap streak bonus
            streak_multiplier = config["streak_multiplier"]
            bonus_exp = streak * streak_multiplier
            exp_gained = math.ceil((base_exp * bonus_exp) + base_exp)

            # Add experience
            guild_user.exp += exp_gained
            guild_user.exp_gained += exp_gained

            # Update global exp
            global_user.global_exp += exp_gained

            # Calculate new level
            new_level = self.calculate_level_from_exp(guild_user.exp)
            guild_user.level = new_level
            global_user.global_level = self.calculate_level_from_exp(global_user.global_exp)

            # Save to database
            guild_user_dao.update_guild_user(guild_user)
            user_dao.update_user(global_user)

            # Set cooldown
            self.set_user_cooldown(user_id, guild_id)

            # Log experience gain
            if streak > 0:
                logger.info(
                    f'{message.author.name} in {message.guild.name} - EXP GAINED = {exp_gained} ({base_exp} base + {exp_gained - base_exp} from {streak}x streak)')
            else:
                logger.info(f'{message.author.name} in {message.guild.name} - EXP GAINED = {exp_gained}')

            # Check for level up
            if new_level > old_level:
                await self.handle_level_up(message, guild_user, old_level, new_level, config)
            else:
                # Even if no level up occurred, check if user is missing roles for their current level
                await self.check_and_apply_missing_roles(message, guild_user, new_level)

        except Exception as e:
            logger.error(f"Error processing message exp for user {user_id} in guild {guild_id}: {e}")
        finally:
            # Close DAOs to return connections to pool
            if guild_user_dao:
                try:
                    guild_user_dao.close()
                except Exception as e:
                    logger.warning(f"Error closing guild_user_dao: {e}")
            if user_dao:
                try:
                    user_dao.close()
                except Exception as e:
                    logger.warning(f"Error closing user_dao: {e}")

    async def handle_level_up(self, message, guild_user, old_level, new_level, config):
        """Handle level up event"""
        guild_user_dao = None
        try:
            user = message.author
            guild = message.guild

            # Calculate level up reward with streak bonus (similar to current system)
            base_reward = config.get("daily_bonus", 1000)
            streak = min(guild_user.streak, config["max_streak_bonus"])  # Cap streak for reward calculation
            streak_multiplier = config["streak_multiplier"]
            streak_bonus_percentage = streak * streak_multiplier
            streak_bonus = math.floor(base_reward * streak_bonus_percentage)
            calculated_reward = base_reward + streak_bonus

            # Update currency with global sync
            guild_user_dao = GuildUserDao()
            try:
                guild_user_dao.update_currency_with_global_sync(
                    user.id,
                    guild.id,
                    calculated_reward
                )
                # Refresh guild_user object to reflect updated currency
                guild_user = guild_user_dao.get_guild_user(user.id, guild.id)
            finally:
                guild_user_dao.close()

            # Send level up announcement if enabled
            if config["level_up_announcements"]:
                # Determine channel to send announcement
                announcement_channel = None

                if config.get("announcement_channel_id"):
                    announcement_channel = guild.get_channel(int(config["announcement_channel_id"]))

                # Fallback to message channel if no specific channel set
                if not announcement_channel:
                    announcement_channel = message.channel

                # Create level up message using custom template
                # Use single template with all placeholders available
                template = config.get("level_up_message",
                    "{username}, you have reached level {level}! Gained {credits} Credits! 🎉")
                level_message = template.format(
                    mention=user.mention,
                    username=user.name,
                    level=new_level,
                    xp=guild_user.exp,
                    credits=f"{calculated_reward:,}",
                    base_credits=f"{base_reward:,}",
                    streak=streak,
                    streak_bonus=f"{streak_bonus:,}"
                )

                try:
                    await announcement_channel.send(level_message)
                    logger.info(f"Sent level up message for {user.name} reaching level {new_level}")
                except discord.Forbidden:
                    logger.warning(f"No permission to send level up message in channel {announcement_channel.id}")
                except Exception as e:
                    logger.error(f"Error sending level up message: {e}")

            # Handle role assignments
            await self.handle_role_assignment(message, guild_user, new_level)

        except Exception as e:
            logger.error(f"Error handling level up: {e}")

    async def handle_role_assignment(self, message, guild_user, new_level):
        """Handle automatic role assignment based on level"""
        guild_dao = None
        try:
            guild = message.guild
            user = message.author
            guild_id = guild.id

            # Get guild settings for role configuration
            guild_dao = GuildDao()
            try:
                guild_obj = guild_dao.get_guild(guild_id)

                if not guild_obj or not guild_obj.settings:
                    return

                settings = json.loads(guild_obj.settings) if isinstance(guild_obj.settings, str) else guild_obj.settings
                roles_config = settings.get("roles", {})
            finally:
                guild_dao.close()

            # Skip if roles system is disabled
            if not roles_config.get("enabled", False):
                return

            role_mappings = roles_config.get("role_mappings", {})
            if not role_mappings:
                return

            # Find roles for this level
            roles_to_add = []
            roles_to_remove = []

            for level_str, role_data in role_mappings.items():
                level_threshold = int(level_str)

                # Handle both old array format and new object format
                if isinstance(role_data, dict):
                    role_ids = role_data.get("role_ids", [])
                else:
                    role_ids = role_data  # Old format (array)

                if new_level >= level_threshold:
                    # User qualifies for these roles
                    for role_id in role_ids:
                        role = guild.get_role(int(role_id))
                        if role and role not in user.roles:
                            roles_to_add.append(role)
                else:
                    # Handle role removal based on mode
                    mode = roles_config.get("mode", "cumulative")
                    if mode == "progressive":
                        # Remove roles from lower levels
                        for role_id in role_ids:
                            role = guild.get_role(int(role_id))
                            if role and role in user.roles:
                                roles_to_remove.append(role)

            # Apply role changes
            if roles_to_add:
                try:
                    await user.add_roles(*roles_to_add, reason=f"Level up to {new_level}")

                    # Send role announcement if enabled
                    if roles_config.get("role_announcement", False):
                        # Get custom announcement message for this level or use default
                        role_mapping_entry = roles_config.get("role_mappings", {}).get(str(new_level))

                        if isinstance(role_mapping_entry, dict):
                            # New format with custom message
                            template = role_mapping_entry.get("announcement_message",
                                "🎉 {mention} reached level {level} and earned the {role} role!")
                        else:
                            # Fallback for old format
                            template = roles_config.get("role_announcement_message",
                                "🎉 {mention} reached level {level} and earned the {role} role!")

                        # Format role mentions
                        role_mentions = [role.mention for role in roles_to_add]
                        if len(role_mentions) == 1:
                            role_str = role_mentions[0]
                        else:
                            role_str = ", ".join(role_mentions)

                        # Format the message
                        announcement_message = template.format(
                            mention=user.mention,
                            username=user.name,
                            level=new_level,
                            role=role_str,
                            roles=role_str
                        )

                        # Determine announcement channel
                        announcement_channel = message.channel
                        if roles_config.get("announcement_channel_id"):
                            channel = guild.get_channel(int(roles_config["announcement_channel_id"]))
                            if channel:
                                announcement_channel = channel

                        await announcement_channel.send(announcement_message)

                except discord.Forbidden:
                    logger.warning(f"No permission to add roles to user {user.id} in guild {guild_id}")
                except Exception as e:
                    logger.error(f"Error adding roles: {e}")

            if roles_to_remove:
                try:
                    await user.remove_roles(*roles_to_remove, reason=f"Progressive role removal at level {new_level}")
                except discord.Forbidden:
                    logger.warning(f"No permission to remove roles from user {user.id} in guild {guild_id}")
                except Exception as e:
                    logger.error(f"Error removing roles: {e}")

        except Exception as e:
            logger.error(f"Error handling role assignment: {e}")

    async def check_and_apply_missing_roles(self, message, guild_user, current_level):
        """Check if user is missing any roles for their current level and apply them"""
        guild_dao = None
        try:
            guild = message.guild
            user = message.author
            guild_id = guild.id

            # Get guild settings for role configuration
            guild_dao = GuildDao()
            try:
                guild_obj = guild_dao.get_guild(guild_id)

                if not guild_obj or not guild_obj.settings:
                    return

                settings = json.loads(guild_obj.settings) if isinstance(guild_obj.settings, str) else guild_obj.settings
                roles_config = settings.get("roles", {})
            finally:
                guild_dao.close()

            # Skip if roles system is disabled
            if not roles_config.get("enabled", False):
                return

            role_mappings = roles_config.get("role_mappings", {})
            if not role_mappings:
                return

            # Find roles user should have based on current level
            roles_to_add = []
            roles_to_remove = []

            for level_str, role_ids in role_mappings.items():
                level_threshold = int(level_str)

                if current_level >= level_threshold:
                    # User qualifies for these roles
                    for role_id in role_ids:
                        role = guild.get_role(int(role_id))
                        if role and role not in user.roles:
                            roles_to_add.append(role)
                else:
                    # Handle role removal based on mode
                    mode = roles_config.get("mode", "cumulative")
                    if mode == "progressive":
                        # Remove roles from lower levels
                        for role_id in role_ids:
                            role = guild.get_role(int(role_id))
                            if role and role in user.roles:
                                roles_to_remove.append(role)

            # Apply role changes silently (no announcements for catchup)
            if roles_to_add:
                try:
                    await user.add_roles(*roles_to_add, reason=f"Role catchup for level {current_level}")
                    logger.info(
                        f"Applied missing roles to {user.name} for level {current_level}: {[role.name for role in roles_to_add]}")
                except discord.Forbidden:
                    logger.warning(f"No permission to add roles to user {user.id} in guild {guild_id}")
                except Exception as e:
                    logger.error(f"Error adding missing roles: {e}")

            if roles_to_remove:
                try:
                    await user.remove_roles(*roles_to_remove,
                                            reason=f"Progressive role cleanup for level {current_level}")
                    logger.info(
                        f"Removed outdated roles from {user.name} for level {current_level}: {[role.name for role in roles_to_remove]}")
                except discord.Forbidden:
                    logger.warning(f"No permission to remove roles from user {user.id} in guild {guild_id}")
                except Exception as e:
                    logger.error(f"Error removing outdated roles: {e}")

        except Exception as e:
            logger.error(f"Error checking and applying missing roles: {e}")
