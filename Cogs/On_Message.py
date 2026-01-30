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
from Entities.GuildUser import GuildUser
from Entities.User import User
from logger import AppLogger
from Services.DailyCheckCache import get_daily_check_cache

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

    async def get_leveling_config(self, guild_id):
        """Get leveling configuration from guild settings (cached)"""
        from Services.ConfigCache import get_config_cache
        return await get_config_cache().get_leveling_config(guild_id)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        # Skip if not in a guild or if author is a bot
        if not message.guild or message.author.bot:
            return

        # Get guild leveling config
        leveling_config = await self.get_leveling_config(message.guild.id)
        # logger.info(leveling_config)
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

        # Get or create guild user and global user
        guild_user_dao = GuildUserDao()
        user_dao = UserDao()

        current_guild_user = guild_user_dao.get_or_create_guild_user_from_discord(message.author, message.guild.id)
        current_user = user_dao.get_or_create_user_from_discord(message.author)

        if current_guild_user is None:
            # Failed to get/create guild user - log error and return
            logger.error(f"Failed to get/create guild user for {message.author.name} in guild {message.guild.name}")
            return

        if current_user is None:
            # Failed to get/create global user - log error and return
            logger.error(f"Failed to get/create global user for {message.author.name}")
            return

        logger.info(f'Processing message from {message.author} in {message.guild.name}')

        try:
            # Update timestamps in memory (for daily check logic)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            current_guild_user.last_active = now.strftime("%Y-%m-%d %H:%M:%S")

            # Note: Message count is incremented in Leveling.py, not here
            # to avoid double counting

            # Update global stats in memory
            if hasattr(current_user, 'last_seen'):
                current_user.last_seen = now.strftime("%Y-%m-%d %H:%M:%S")

            # Note: last_active and last_seen are now managed by XP sessions
            # and only persisted during periodic flushes (every 5 minutes)

            # CHECK FOR INAPPROPRIATE WORDS
            message_content_lower = message.content.lower()
            for word in self.inappropriate_words:
                if word.lower() in message_content_lower:
                    logger.info(f'{message.author.name} - INAPPROPRIATE WORD DETECTED in {message.guild.name}')
                    await message.delete()
                    return

            # CHECK IF - DAILY REWARD (optimized with daily check cache)
            from Services.PerformanceMonitor import get_performance_monitor

            daily_cache = get_daily_check_cache()
            should_check = await daily_cache.should_check_daily(message.guild.id, message.author.id)

            # Record daily check stats
            perf_monitor = get_performance_monitor()
            if should_check:
                await perf_monitor.record_daily_check_performed()
            else:
                await perf_monitor.record_daily_check_skipped()

            if should_check and current_guild_user.daily == 0:
                logger.info(f"{message.author.name} - COMPLETED DAILY REWARD in {message.guild.name}")
                await self.process_daily_reward(current_guild_user, message.author, daily_reward_channel)

                # Record daily reward in performance monitor
                from Services.PerformanceMonitor import get_performance_monitor
                perf_monitor = get_performance_monitor()
                await perf_monitor.record_daily_reward()

                # ONLY save to database after daily reward
                guild_user_dao.update_guild_user(current_guild_user)
                user_dao.update_user(current_user)
                logger.info(f'{message.author} database updated after daily reward in guild {message.guild.name}')

            # Note: Regular messages no longer trigger DB writes!
            # XP system handles all updates via sessions (flushed every 5 minutes)

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
        """Process daily reward for guild user, including bank interest."""

        try:
            # Get the global user for bank balance
            user_dao = UserDao()
            global_user = user_dao.get_user(member.id)
            if not global_user:
                logger.error(f"Could not find global user for {member.name} during daily reward.")
                # Create a temporary user object to prevent crashes, though interest will be 0
                global_user = User(id=member.id, discord_username=member.name, bank_balance=0)

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
                elif last_daily_date < today - timedelta(days=1):
                    # Reset streak
                    guild_user.streak = 1
            
            # CALCULATE AND PAY BANK INTEREST (20% APR) - ONCE PER DAY GLOBALLY
            # Note: This is checked per-guild daily, but paid only once globally per day
            interest_amount = 0
            interest_paid = False

            if global_user.bank_balance > 0:
                daily_rate = 0.20 / 365
                potential_interest = math.floor(global_user.bank_balance * daily_rate)
                if potential_interest > 0:
                    # This method checks if interest was already paid today and only pays once
                    # Pass guild_id to track which server triggered the interest payout
                    interest_paid = user_dao.add_bank_interest(member.id, potential_interest, member.guild.id)
                    if interest_paid:
                        interest_amount = potential_interest
                        logger.info(f"Paid {interest_amount} interest to user {member.name} (ID: {member.id})")
                    else:
                        logger.debug(f"Interest already paid today for user {member.name} (ID: {member.id})")

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
            guild_user.currency += calculated_daily_reward
            
            # Set daily and last_daily
            guild_user.daily = 1
            guild_user.last_daily = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

            # Save other updated fields (currency already saved by sync method)
            guild_user_dao.update_guild_user(guild_user)

            # Send daily reward message using custom template
            if daily_channel:
                leveling_config = await self.get_leveling_config(member.guild.id)
                if streak > 1:
                    template = leveling_config.get("daily_announcement_message_with_streak",
                        "💰 {mention} claimed their daily reward! +{credits} Credits! ({base_credits} + {streak_bonus} from {streak}x streak!)")
                else:
                    template = leveling_config.get("daily_announcement_message",
                        "💰 {username} claimed their daily reward! +{credits} Credits!")

                message = template.format(
                    mention=member.mention,
                    username=member.name,
                    credits=f"{calculated_daily_reward:,}",
                    base_credits=f"{base_daily:,}",
                    streak=streak,
                    streak_bonus=f"{streak_bonus:,}"
                )

                # Only show interest message if it was actually paid (not already paid today)
                if interest_paid and interest_amount > 0:
                    message += f"\n> You also earned **{interest_amount:,}** credits in daily interest from your bank balance! 📈"

                await daily_channel.send(message)

        except Exception as e:
            logger.error(f'Error processing daily reward for {member.name}: {e}')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Message(bot))