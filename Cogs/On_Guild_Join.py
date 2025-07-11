import discord
from discord.ext import commands
from datetime import datetime
from Dao.GuildDao import GuildDao
from Dao.GuildUserDao import GuildUserDao
from Entities.Guild import Guild
from Entities.GuildUser import GuildUser
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

            # Create guild record
            await self._create_guild_record(guild, guild_dao)

            # Add all existing members to the database
            await self._add_guild_members(guild, guild_user_dao)

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
                    last_active=formatted_join_date
                )

                if guild_dao.add_new_guild(new_guild):
                    logger.info(f"Created guild record for {guild.name}")
                else:
                    logger.error(f"Failed to create guild record for {guild.name}")

        except Exception as e:
            logger.error(f"Error creating guild record for {guild.name}: {e}")

    async def _add_guild_members(self, guild: discord.Guild, guild_user_dao: GuildUserDao):
        """
        Add all current guild members to the database.
        """
        try:
            members_added = 0
            members_updated = 0

            for member in guild.members:
                if member.bot:
                    continue  # Skip bots

                # Check if guild user already exists
                existing_guild_user = guild_user_dao.get_guild_user(member.id, guild.id)

                if existing_guild_user:
                    # Reactivate if they were previously deactivated
                    if not existing_guild_user.is_active:
                        guild_user_dao.activate_guild_user(member.id, guild.id)
                        members_updated += 1
                        logger.info(f"Reactivated guild user: {member.name} in {guild.name}")
                else:
                    # Create new guild user record
                    formatted_join_date = member.joined_at.strftime(
                        "%Y-%m-%d %H:%M:%S") if member.joined_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    new_guild_user = GuildUser(
                        user_id=member.id,
                        guild_id=guild.id,
                        nickname=member.display_name,
                        level=0,
                        season_level=0,
                        season_exp=0,
                        streak=0,
                        highest_streak=0,
                        exp=0,
                        exp_gained=0,
                        exp_lost=0,
                        currency=0,  # Starting currency for new users
                        messages_sent=0,
                        reactions_sent=0,
                        joined_at=formatted_join_date,
                        last_active=formatted_join_date,
                        daily=0,
                        last_daily=None,
                        is_active=True
                    )

                    if guild_user_dao.add_guild_user(new_guild_user):
                        members_added += 1
                    else:
                        logger.error(f"Failed to add guild user: {member.name} to {guild.name}")

            logger.info(
                f"Guild member processing complete for {guild.name}: {members_added} added, {members_updated} reactivated")

        except Exception as e:
            logger.error(f"Error adding guild members for {guild.name}: {e}")

    async def _send_welcome_message(self, guild: discord.Guild):
        """
        Send a welcome message to the guild.
        """
        try:
            # Look for common channel names to send welcome message
            welcome_channels = ['general', 'welcome', 'bot-commands', 'commands']

            target_channel = None

            # Try to find a suitable channel
            for channel in guild.text_channels:
                if channel.name.lower() in welcome_channels:
                    if channel.permissions_for(guild.me).send_messages:
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
                    value="• Leveling system with XP and rewards\n• Economy with Credits\n• Fun games like slots, coinflip, and more\n• Leaderboards and stats",
                    inline=False
                )

                # embed.add_field(
                #     name="⚙️ Setup",
                #     value="The bot is ready to use! All databases have been initialized.",
                #     inline=False
                # )

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