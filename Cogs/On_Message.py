from datetime import datetime, timedelta, timezone
import os
import json
import math
import random
from typing import Optional
import discord
from discord import Message
from discord.ext import commands
from dotenv import load_dotenv
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Dao.GuildDao import GuildDao
from Entities.GuildUser import GuildUser
from Entities.User import User
from logger import AppLogger

# Load environment variables from .env file
load_dotenv()

logger = AppLogger(__name__).get_logger()


class On_Message(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.guildUserDao = GuildUserDao()
        self.userDao = UserDao()
        load_dotenv()
        inappropriate_words_str = os.getenv('INAPPROPRIATE_WORDS')
        if inappropriate_words_str:
            self.inappropriate_words = json.loads(inappropriate_words_str)
        else:
            self.inappropriate_words = []

    def find_channel_by_name(self, guild: discord.Guild, channel_names: list) -> discord.TextChannel:
        """Find a channel by name in the guild, accounting for emojis and special characters"""
        for name in channel_names:
            # First try exact match
            channel = discord.utils.get(guild.text_channels, name=name)
            if channel and channel.permissions_for(guild.me).send_messages:
                return channel

            # If no exact match, try partial matching (case-insensitive)
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    # Remove emojis and special characters for comparison
                    clean_channel_name = self.clean_channel_name(channel.name.lower())
                    clean_search_name = self.clean_channel_name(name.lower())

                    # Check if the search term is in the channel name
                    if clean_search_name in clean_channel_name:
                        return channel

        # Fallback: find any channel the bot can send messages to
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel

        return None

    def clean_channel_name(self, name: str) -> str:
        """Remove emojis, special characters, and separators from channel name"""
        import re

        # Remove emojis (Unicode emoji pattern)
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                   u"\U00002702-\U000027B0"  # Dingbats
                                   u"\U000024C2-\U0001F251"
                                   "]+", flags=re.UNICODE)

        cleaned = emoji_pattern.sub('', name)

        # Remove common separators and special characters
        cleaned = re.sub(r'[︱｜|‖∥]', '', cleaned)  # Various vertical bar characters
        cleaned = re.sub(r'[-_\s]+', '', cleaned)  # Hyphens, underscores, spaces
        cleaned = re.sub(r'[^\w]', '', cleaned)  # Any remaining non-word characters

        return cleaned.strip()

    def get_leveling_config(self, guild_id):
        """Get leveling configuration from guild settings"""
        default_config = {
            "enabled": True,
            "daily_announcements_enabled": False,
            "daily_announcement_channel_id": None
        }

        try:
            guild_dao = GuildDao()
            guild = guild_dao.get_guild(guild_id)

            if not guild or not guild.settings:
                return default_config

            # Parse settings JSON
            settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings

            # Get leveling settings or return default
            leveling_settings = settings.get("leveling", {})

            # Merge with defaults
            config = default_config.copy()
            config.update(leveling_settings)

            return config

        except Exception as e:
            logger.error(f"Error getting leveling config for guild {guild_id}: {e}")
            return default_config

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        # Skip if not in a guild or if author is a bot
        if not message.guild or message.author.bot:
            return

        # Get guild leveling config
        leveling_config = self.get_leveling_config(message.guild.id)

        # Skip if leveling is disabled
        if not leveling_config.get("enabled", True):
            return

        # Determine daily reward announcement channel
        daily_reward_channel = None
        if leveling_config.get("daily_announcements_enabled", False):
            # Use configured channel if set
            if leveling_config.get("daily_announcement_channel_id"):
                daily_reward_channel = message.guild.get_channel(int(leveling_config["daily_announcement_channel_id"]))

            # Fallback to searching by name if no channel configured or channel not found
            if not daily_reward_channel:
                daily_reward_channel = self.find_channel_by_name(message.guild,
                                                                 ['daily-rewards', 'daily', 'rewards', 'bot-updates',
                                                                  'general'])

        # Get guild-specific roles
        inmate_role = discord.utils.get(message.guild.roles, name='Inmate')

        # Skip processing if user is in jail
        if inmate_role and inmate_role in message.author.roles:
            logger.info(f'{message.author} is an inmate in {message.guild.name} - skipped processing')
            return

        # Get or create guild user and global user
        guild_user_dao = GuildUserDao()
        user_dao = UserDao()

        current_guild_user = guild_user_dao.get_or_create_guild_user_from_discord(message.author, message.guild.id)
        current_user = user_dao.get_or_create_user_from_discord(message.author)

        if current_guild_user is None:
            # Failed to get/create guild user - log error and return
            print(f"Failed to get/create guild user for {message.author.name}")
            return

        if current_user is None:
            # Failed to get/create global user - log error and return
            print(f"Failed to get/create global user for {message.author.name}")
            return

        logger.info(f'Processing message from {message.author} in {message.guild.name}')

        try:
            # Update last active timestamp
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            current_guild_user.last_active = now.strftime("%Y-%m-%d %H:%M:%S")

            # Note: Message count is incremented in Leveling.py, not here
            # to avoid double counting

            # Update global stats
            if hasattr(current_user, 'last_seen'):
                current_user.last_seen = now.strftime("%Y-%m-%d %H:%M:%S")

            # CHECK FOR INAPPROPRIATE WORDS
            message_content_lower = message.content.lower()
            for word in self.inappropriate_words:
                if word.lower() in message_content_lower:
                    logger.info(f'{message.author.name} - INAPPROPRIATE WORD DETECTED in {message.guild.name}')
                    await message.delete()
                    return

            # CHECK IF - DAILY REWARD
            if current_guild_user.daily == 0:
                logger.info(f"{message.author.name} - COMPLETED DAILY REWARD in {message.guild.name}")
                await self.process_daily_reward(current_guild_user, message.author, daily_reward_channel)

            # SAVE TO DATABASE
            guild_user_dao.update_guild_user(current_guild_user)
            user_dao.update_user(current_user)
            logger.info(f'{message.author} updated in database for guild {message.guild.name}')

            # OTHER REACTIONS
            if message.content.lower() == "yo":
                try:
                    yo_emojis = ["🖕", "🍆", "🤝", "🦉", "🤡", "😘", "👋", "👽", "🤙"]
                    await message.add_reaction(random.choice(yo_emojis))
                except:
                    pass  # If reaction fails, just continue

        except Exception as e:
            logger.error(f'Error processing message from {message.author} in {message.guild.name}: {e}')

    async def process_daily_reward(self, guild_user: GuildUser, member: discord.Member,
                                   daily_channel: Optional[discord.TextChannel]):
        """Process daily reward for guild user"""
        try:
            today = datetime.now(timezone.utc).replace(tzinfo=None).date()

            if guild_user.last_daily is None:
                guild_user.streak = 1
            else:
                last_daily_date = guild_user.last_daily
                if isinstance(last_daily_date, str):
                    last_daily_date = datetime.strptime(last_daily_date, "%Y-%m-%d %H:%M:%S").date()
                elif isinstance(last_daily_date, datetime):
                    last_daily_date = last_daily_date.date()

                if last_daily_date == today - timedelta(days=1):
                    # Increment streak
                    guild_user.streak += 1
                    if guild_user.streak > guild_user.highest_streak:
                        guild_user.highest_streak = guild_user.streak
                        logger.info(f"{member.name} - HIGHEST STREAK INCREMENTED TO {guild_user.highest_streak}")
                    logger.info(f"{member.name} - STREAK INCREMENTED TO {guild_user.streak}")
                elif last_daily_date < today - timedelta(days=1):
                    # Reset streak
                    guild_user.streak = 1
                    logger.info(f"{member.name} - STREAK RESET TO {guild_user.streak}")

            # CALCULATE DAILY REWARD
            base_daily = 100
            streak = guild_user.streak if guild_user.streak < 20 else 20
            base_bonus_multiplier = 0.05
            streak_bonus_percentage = streak * base_bonus_multiplier
            streak_bonus = math.floor(base_daily * streak_bonus_percentage)
            calculated_daily_reward = base_daily + streak_bonus

            # Update currency with global sync
            guild_user_dao = GuildUserDao()
            guild_user_dao.update_currency_with_global_sync(
                member.id,
                member.guild.id,
                calculated_daily_reward
            )

            # Set daily and last_daily
            guild_user.daily = 1
            guild_user.last_daily = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

            # Save other updated fields (currency already saved by sync method)
            guild_user_dao.update_guild_user(guild_user)

            # Send daily reward message using custom template
            if daily_channel:
                # Get leveling config for custom message templates
                leveling_config = self.get_leveling_config(member.guild.id)

                # Use single template with all placeholders available
                template = leveling_config.get("daily_announcement_message",
                    "{username} claimed their daily reward! +{credits} Credits! 💰")
                message = template.format(
                    mention=member.mention,
                    username=member.name,
                    credits=f"{calculated_daily_reward:,}",
                    base_credits=f"{base_daily:,}",
                    streak=streak,
                    streak_bonus=f"{streak_bonus:,}"
                )

                await daily_channel.send(message)

        except Exception as e:
            logger.error(f'Error processing daily reward for {member.name}: {e}')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Message(bot))