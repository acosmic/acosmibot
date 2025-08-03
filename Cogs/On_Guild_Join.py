from operator import truediv

import discord
from discord.ext import commands
from datetime import datetime
from Dao.GuildDao import GuildDao
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Entities.Guild import Guild
from Entities.GuildUser import GuildUser
from Entities.User import User
from logger import AppLogger
import os
from dotenv import load_dotenv

load_dotenv()
logger = AppLogger(__name__).get_logger()


class On_Guild_Join(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        Event triggered when the bot joins a new guild.
        Creates guild record and adds all existing members to the database.
        """
        try:
            logger.info(f"Bot joined guild: {guild.name} (ID: {guild.id})")

            # Initialize DAOs
            guild_dao = GuildDao()
            guild_user_dao = GuildUserDao()
            user_dao = UserDao()

            # Create guild record
            await self._create_guild_record(guild, guild_dao)

            # Add all existing members to the database (both global and guild-specific)
            await self._add_guild_members(guild, guild_user_dao, user_dao)

            # Send welcome message to a general channel if possible
            await self._send_welcome_message(guild)

            logger.info(f"Successfully processed guild join for {guild.name}")

        except Exception as e:
            logger.error(f"Error processing guild join for {guild.name}: {e}")

    async def _create_guild_record(self, guild: discord.Guild, guild_dao: GuildDao):
        """
        Create a database record for the new guild.
        """
        try:
            # Check if guild already exists
            existing_guild = guild_dao.get_guild(guild.id)

            if existing_guild:
                logger.info(f"Guild {guild.name} already exists in database, updating...")
                # Update existing guild info
                existing_guild.name = guild.name
                existing_guild.owner_id = guild.owner_id
                existing_guild.member_count = guild.member_count
                existing_guild.active = True
                existing_guild.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                guild_dao.update_guild(existing_guild)
            else:
                # Create new guild record
                formatted_join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                new_guild = Guild(
                    id=guild.id,
                    name=guild.name,
                    owner_id=guild.owner_id,
                    member_count=guild.member_count,
                    active=True,
                    settings=None,  # Can be expanded later for guild-specific settings
                    created=formatted_join_date,
                    last_active=formatted_join_date,
                    vault_currency=0,  # Default vault currency
                    ai_enabled=True,  # AI enabled by default
                    ai_thread_id=None,  # Will be set when AI is first used
                    ai_temperature=1.0,  # Default temperature
                    ai_personality_traits={
                        "humor_level": "high",
                        "sarcasm_level": "medium",
                        "nerd_level": "high",
                        "friendliness": "high"
                    }  # Default personality traits
                )

                if guild_dao.add_new_guild(new_guild):
                    logger.info(f"Created guild record for {guild.name}")
                else:
                    logger.error(f"Failed to create guild record for {guild.name}")

        except Exception as e:
            logger.error(f"Error creating guild record for {guild.name}: {e}")

    async def _add_guild_members(self, guild: discord.Guild, guild_user_dao: GuildUserDao, user_dao: UserDao):
        """
        Add all current guild members to the database (both global and guild-specific).
        """
        try:
            guild_users_added = 0
            guild_users_updated = 0
            global_users_added = 0
            global_users_updated = 0

            for member in guild.members:
                if member.bot:
                    continue  # Skip bots

                # Handle global user first
                existing_global_user = user_dao.get_user(member.id)

                if existing_global_user:
                    # Update existing global user
                    existing_global_user._discord_username = member.name
                    existing_global_user._global_name = member.global_name if hasattr(member,
                                                                                      'global_name') else member.name
                    existing_global_user._avatar_url = str(
                        member.avatar.url) if member.avatar else existing_global_user.avatar_url
                    existing_global_user._last_seen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    user_dao.update_user(existing_global_user)
                    global_users_updated += 1
                    logger.info(f"Updated global user: {member.name}")
                else:
                    # Create new global user
                    formatted_creation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    try:
                        account_created = member.created_at.strftime(
                            "%Y-%m-%d %H:%M:%S") if member.created_at else formatted_creation_date
                    except Exception:
                        account_created = formatted_creation_date

                    new_global_user = User(
                        id=member.id,
                        discord_username=member.name,
                        global_name=member.global_name if hasattr(member, 'global_name') else member.name,
                        avatar_url=str(member.avatar.url) if member.avatar else None,
                        is_bot=member.bot,
                        global_exp=0,
                        global_level=0,
                        total_currency=0,
                        total_messages=0,
                        total_reactions=0,
                        account_created=account_created,
                        first_seen=formatted_creation_date,
                        last_seen=formatted_creation_date,
                        privacy_settings=None,
                        global_settings=None
                    )

                    if user_dao.add_user(new_global_user):
                        global_users_added += 1
                        logger.info(f"Created new global user: {member.name}")
                    else:
                        logger.error(f"Failed to create global user: {member.name}")

                # Handle guild user
                existing_guild_user = guild_user_dao.get_guild_user(member.id, guild.id)

                if existing_guild_user:
                    # Update name, nickname, and reactivate in one call
                    existing_guild_user.name = member.name
                    existing_guild_user.nickname = member.display_name
                    existing_guild_user.is_active = True
                    guild_user_dao.update_guild_user(existing_guild_user)
                    guild_users_updated += 1
                    logger.info(f"Updated guild user: {member.name} (nickname: {member.display_name}) in {guild.name}")
                else:
                    # Create new guild user record
                    formatted_join_date = member.joined_at.strftime(
                        "%Y-%m-%d %H:%M:%S") if member.joined_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    new_guild_user = GuildUser(
                        user_id=member.id,
                        guild_id=guild.id,
                        name=member.name,
                        nickname=member.display_name,
                        level=0,
                        streak=0,
                        highest_streak=0,
                        exp=0,
                        exp_gained=0,
                        exp_lost=0,
                        currency=1000,  # Starting currency for new users
                        messages_sent=0,
                        reactions_sent=0,
                        joined_at=formatted_join_date,
                        last_active=formatted_join_date,
                        daily=0,
                        last_daily=None,
                        is_active=True
                    )

                    if guild_user_dao.add_guild_user(new_guild_user):
                        guild_users_added += 1
                    else:
                        logger.error(f"Failed to add guild user: {member.name} to {guild.name}")

            logger.info(
                f"Member processing complete for {guild.name}: "
                f"Global users: {global_users_added} added, {global_users_updated} updated | "
                f"Guild users: {guild_users_added} added, {guild_users_updated} reactivated"
            )

        except Exception as e:
            logger.error(f"Error adding guild members for {guild.name}: {e}")

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

    async def _send_welcome_message(self, guild: discord.Guild):
        """
        Send a welcome message to the guild.
        """
        try:
            # Look for common channel names to send welcome message
            welcome_channels = ['general', 'welcome', 'botcommands', 'commands', 'chat', 'main']

            target_channel = None

            # Try to find a suitable channel using cleaned names
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    # Check both original and cleaned channel names
                    original_name = channel.name.lower()
                    cleaned_name = self.clean_channel_name(channel.name).lower()

                    if original_name in welcome_channels or cleaned_name in welcome_channels:
                        target_channel = channel
                        break

            # If no specific channel found, use the first channel the bot can send messages to
            if not target_channel:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        target_channel = channel
                        break

            if target_channel:
                embed = discord.Embed(
                    title="🎉 Thank you for adding Acosmibot!",
                    description="I'm excited to be part of your server!",
                    color=discord.Color.blue()
                )

                embed.add_field(
                    name="🚀 Getting Started",
                    value="Use `/help` to see all available commands!",
                    inline=False
                )

                embed.add_field(
                    name="🎮 Features",
                    value="• Leveling system with XP and rewards\n• Economy with Credits\n• Fun games like slots, coinflip, and more\n• AI chat capabilities\n• Leaderboards and stats",
                    inline=False
                )

                embed.add_field(
                    name="🤖 AI Features",
                    value="• AI-powered conversations\n• Customizable personality traits\n• Contextual responses\n• Use AI commands to get started!",
                    inline=False
                )

                embed.set_footer(text="Developed by Acosmic")

                await target_channel.send(embed=embed)
                logger.info(f"Sent welcome message to {guild.name} in #{target_channel.name}")
            else:
                logger.warning(f"Could not find a suitable channel to send welcome message in {guild.name}")

        except Exception as e:
            logger.error(f"Error sending welcome message to {guild.name}: {e}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        Event triggered when the bot leaves a guild.
        Deactivates the guild in the database.
        """
        try:
            logger.info(f"Bot left guild: {guild.name} (ID: {guild.id})")

            guild_dao = GuildDao()
            guild_user_dao = GuildUserDao()

            # Deactivate guild
            existing_guild = guild_dao.get_guild(guild.id)
            if existing_guild:
                existing_guild.active = False
                existing_guild.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                guild_dao.update_guild(existing_guild)
                logger.info(f"Deactivated guild: {guild.name}")

            # Deactivate all guild users
            guild_users = guild_user_dao.get_guild_users(guild.id)
            for guild_user in guild_users:
                guild_user_dao.deactivate_guild_user(guild_user.user_id, guild.id)

            logger.info(f"Deactivated {len(guild_users)} users from guild: {guild.name}")

        except Exception as e:
            logger.error(f"Error processing guild leave for {guild.name}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Guild_Join(bot))