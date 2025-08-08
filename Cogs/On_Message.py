from datetime import datetime, timedelta
import os
import json
import math
from typing import Optional
import discord
from discord import Message
from discord.ext import commands
from dotenv import load_dotenv
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Entities.GuildUser import GuildUser
from Entities.User import User
from Leveling import Leveling
from logger import AppLogger

# Load environment variables from .env file
load_dotenv()

# role_level_1 = os.getenv('ROLE_LEVEL_1')
# role_level_2 = os.getenv('ROLE_LEVEL_2')
# role_level_3 = os.getenv('ROLE_LEVEL_3')
# role_level_4 = os.getenv('ROLE_LEVEL_4')
# role_level_5 = os.getenv('ROLE_LEVEL_5')
# role_level_6 = os.getenv('ROLE_LEVEL_6')
# role_level_7 = os.getenv('ROLE_LEVEL_7')

logger = AppLogger(__name__).get_logger()


class On_Message(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
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

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        # Skip if not in a guild or if author is a bot
        if not message.guild or message.author.bot:
            return

        # Find appropriate channels for this guild
        level_up_channel = self.find_channel_by_name(message.guild,
                                                     ['level-up', 'levelup', 'levels', 'bot-updates', 'general'])
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

        current_guild_user = guild_user_dao.get_guild_user(message.author.id, message.guild.id)
        current_user = user_dao.get_user(message.author.id)

        if current_guild_user is None:
            current_guild_user = await self.create_new_guild_user(message.author, message.guild, guild_user_dao)
            if not current_guild_user:
                return

        if current_user is None:
            current_user = await self.create_new_global_user(message.author, user_dao)
            if not current_user:
                return

        logger.info(f'Processing message from {message.author} in {message.guild.name}')

        try:
            # SPAM PROTECTION
            last_active = current_guild_user.last_active
            now = datetime.now()
            if isinstance(last_active, str):
                last_active = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S")

            if now - last_active > timedelta(seconds=4):
                base_exp = 10
            else:
                base_exp = 0
                logger.info(f'{message.author.name} - MESSAGE SENT TOO SOON - NO EXP GAINED')

            # CHECK FOR INAPPROPRIATE WORDS
            message_content_lower = message.content.lower()
            for word in self.inappropriate_words:
                if word.lower() in message_content_lower:
                    logger.info(f'{message.author.name} - INAPPROPRIATE WORD DETECTED in {message.guild.name}')
                    await message.delete()
                    return

            # CALCULATE EXP GAINED
            bonus_exp = current_guild_user.streak * 0.05
            exp_gain = math.ceil((base_exp * bonus_exp) + base_exp)

            # Update guild-specific exp
            current_guild_user.exp += exp_gain
            current_guild_user.exp_gained += exp_gain
            current_guild_user.messages_sent += 1
            current_guild_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Update global exp and stats (with safe attribute access)
            if hasattr(current_user, 'global_exp'):
                current_user.global_exp += exp_gain
            if hasattr(current_user, 'total_messages'):
                current_user.total_messages += 1
            if hasattr(current_user, 'last_seen'):
                current_user.last_seen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            logger.info(f'{message.author.name} in {message.guild.name} - EXP GAINED = {exp_gain} (Guild + Global)')

            # CHECK IF - DAILY REWARD
            if current_guild_user.daily == 0:
                logger.info(f"{message.author.name} - COMPLETED DAILY REWARD in {message.guild.name}")
                await self.process_daily_reward(current_guild_user, message.author, daily_reward_channel)

            # CHECK IF - GUILD LEVELING UP
            lvl = Leveling()
            new_guild_level = lvl.calc_level(current_guild_user.exp)

            # GUILD LEVEL UP
            if new_guild_level > current_guild_user.level:
                await self.process_level_up(current_guild_user, message.author, new_guild_level, level_up_channel,
                                            level_type="GUILD")

            current_guild_user.level = new_guild_level

            # CHECK IF - GLOBAL LEVELING UP (with safe attribute access)
            if hasattr(current_user, 'global_exp') and hasattr(current_user, 'global_level'):
                new_global_level = lvl.calc_level(current_user.global_exp)

                # GLOBAL LEVEL UP
                if new_global_level > current_user.global_level:
                    await self.process_level_up(current_guild_user, message.author, new_global_level, level_up_channel,
                                                level_type="ACOSMIBOT", user_obj=current_user)

                current_user.global_level = new_global_level

                # UPDATE ROLES (based on global level now)
                # await self.update_user_roles(current_user, message.author, message.guild)

            # SAVE TO DATABASE
            guild_user_dao.update_guild_user(current_guild_user)
            user_dao.update_user(current_user)
            logger.info(f'{message.author} updated in database for guild {message.guild.name}')

            # OTHER REACTIONS
            if message.content.lower() == "yo":
                try:
                    await message.add_reaction("👋")  # Using standard wave emoji as fallback
                except:
                    pass  # If reaction fails, just continue

        except Exception as e:
            logger.error(f'Error processing message from {message.author} in {message.guild.name}: {e}')

    async def process_daily_reward(self, guild_user: GuildUser, member: discord.Member,
                                   daily_channel: Optional[discord.TextChannel]):
        """Process daily reward for guild user"""
        try:
            today = datetime.now().date()

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
            guild_user.currency += calculated_daily_reward

            # Set daily and last_daily
            guild_user.daily = 1
            guild_user.last_daily = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Send daily reward message
            if daily_channel:
                if streak > 0:
                    await daily_channel.send(
                        f'## {member.mention}, You have collected your daily reward - {calculated_daily_reward} Credits! 100 + {streak_bonus} from {streak}x Streak! 🎉')
                else:
                    await daily_channel.send(
                        f'## {member.mention}, You have collected your daily reward - 100 Credits! 🎉')

        except Exception as e:
            logger.error(f'Error processing daily reward for {member.name}: {e}')

    async def process_level_up(self, guild_user: GuildUser, member: discord.Member, new_level: int,
                               level_channel: Optional[discord.TextChannel], level_type: str = "GUILD",
                               user_obj: Optional[User] = None):
        """Process level up for guild user or global user"""
        try:
            # CALCULATE LEVEL UP REWARD
            if level_type == "ACOSMIBOT":
                base_reward = 5000
                emoji = "🤖"
            else:
                base_reward = 1000
                emoji = "🎉"

            streak = guild_user.streak if guild_user.streak < 20 else 20
            base_bonus_multiplier = 0.05
            streak_bonus_percentage = streak * base_bonus_multiplier
            streak_bonus = math.floor(base_reward * streak_bonus_percentage)
            calculated_reward = base_reward + streak_bonus
            guild_user.currency += calculated_reward

            # Send level up message
            if level_channel:
                if streak > 0:
                    await level_channel.send(
                        f'## {emoji} {member.mention} {level_type} LEVEL UP! You have reached level {new_level}! Gained {calculated_reward} Credits! {base_reward:,} + {streak_bonus} from {streak}x Streak! {emoji}')
                else:
                    await level_channel.send(
                        f'## {emoji} {member.mention} {level_type} LEVEL UP! You have reached level {new_level}! Gained {calculated_reward} Credits! {emoji}')

        except Exception as e:
            logger.error(f'Error processing level up for {member.name}: {e}')

    async def update_user_roles(self, user: User, member: discord.Member, guild: discord.Guild):
        """Update user roles based on global level"""
        try:
            # Check if user has global_level attribute
            if not hasattr(user, 'global_level'):
                logger.warning(f"User {member.name} does not have global_level attribute")
                return

            user_roles = member.roles
            roles_to_add = []

            # Define role thresholds based on global level
            role_thresholds = [
                (0, role_level_1),
                (5, role_level_2),
                (10, role_level_3),
                (15, role_level_4),
                (20, role_level_5),
                (25, role_level_6),
                (30, role_level_7)
            ]

            # Find the highest role the user qualifies for
            for threshold, role_name in reversed(role_thresholds):
                if user.global_level >= threshold and role_name:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role and role not in user_roles:
                        roles_to_add.append(role)
                        break  # Only add the highest qualifying role

            # Add roles
            if roles_to_add:
                await member.add_roles(*roles_to_add)
                logger.info(f'Added roles to {member.name} in {guild.name}: {[role.name for role in roles_to_add]}')

        except Exception as e:
            logger.error(f'Error updating roles for {member.name} in {guild.name}: {e}')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Message(bot))