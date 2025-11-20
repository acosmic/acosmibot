#! /usr/bin/python3.10
import sys
import discord
from discord.ext import commands
from logger import AppLogger
from Tasks.task_manager import register_tasks
from Cogs import __all__ as enabled_cogs
from models.settings_manager import SettingsManager
from Dao.GuildDao import GuildDao
from database import Database


logger = AppLogger(__name__).get_logger()


class Bot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        super().__init__(command_prefix=commands.when_mentioned_or('!'), intents=intents)
        self.posted = False

    async def on_command_error(self, ctx, error):
        """Handle command errors globally"""
        # Suppress CommandNotFound errors (these happen when someone mentions the bot with non-commands)
        if isinstance(error, commands.CommandNotFound):
            # Don't log these errors since they're expected when using AI chat
            return

        # Log other errors normally
        logger.error(f"Command error in {ctx.guild.name if ctx.guild else 'DM'}: {error}")

    async def setup_hook(self):
        # Initialize SettingsManager singleton on bot startup
        try:
            guild_dao = GuildDao()
            SettingsManager(guild_dao)
            guild_dao.close()  # Close the DAO after setup
            logger.info("SettingsManager singleton initialized")
        except Exception as e:
            logger.error(f"Failed to initialize SettingsManager: {e}")
            raise

        register_tasks(self)
        for cog_name in enabled_cogs:
            ext = f"Cogs.{cog_name}"
            try:
                if ext not in self.extensions:
                    await self.load_extension(ext)
                    logger.info(f'{ext} loaded')
            except Exception as e:
                logger.error(f'Failed to load {ext}: {e}')

    async def close(self):
        """Close the bot and clean up database connections"""
        logger.info("Bot shutting down, closing database connection pools...")
        try:
            Database.close_all_pools()
            logger.info("Database connection pools closed successfully")
        except Exception as e:
            logger.error(f"Error closing database pools: {e}")
        await super().close()

    async def on_ready(self):
        logger.info(f'Logged on as {self.user}!')
        synced = await self.tree.sync()
        logger.info(f"slash cmd's synced: {str(len(synced))}")
        logger.info(f"discord.py version: {discord.__version__}")
        logger.info(f"python version: {str(sys.version)}")


        await self.change_presence(activity=discord.CustomActivity('/help • acosmibot.com'))
