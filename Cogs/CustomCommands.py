#! /usr/bin/python3.10
"""
Custom Commands Cog

Listens to messages and executes custom commands created by guilds.
Premium feature: Free tier = 1 command, Premium tier = 25 commands.
"""
import discord
from discord.ext import commands
from models.custom_command_manager import CustomCommandManager
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class CustomCommands(commands.Cog):
    """Cog for executing custom commands"""

    def __init__(self, bot):
        self.bot = bot
        self.manager = CustomCommandManager()
        logger.info("CustomCommands cog loaded")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listen for messages that might be custom commands

        Args:
            message: Discord message object
        """
        # Skip if bot message
        if message.author.bot:
            return

        # Skip if DM (custom commands are guild-only)
        if not message.guild:
            return

        # Skip if message starts with '/' (slash command)
        if message.content.startswith('/'):
            return

        # Skip if bot is mentioned (AI chat handles this)
        if self.bot.user in message.mentions:
            return

        # Skip if empty message
        if not message.content or not message.content.strip():
            return

        # Try to parse as custom command
        await self._try_execute_custom_command(message)

    async def _try_execute_custom_command(self, message: discord.Message):
        """
        Check if message is a custom command and execute it

        Args:
            message: Discord message object
        """
        content = message.content.strip()

        # Get all enabled custom commands for this guild
        commands_list = self.manager.get_guild_commands(
            guild_id=message.guild.id,
            enabled_only=True,
            use_cache=True
        )

        if not commands_list:
            return  # No custom commands for this guild

        # Check if message matches any custom command
        for cmd in commands_list:
            full_command = cmd.get_full_command()  # e.g., "!welcome"

            # Check if message starts with this command
            # Support both exact match and command with arguments
            if content == full_command or content.startswith(full_command + ' '):
                try:
                    await self._execute_command(message, cmd)
                    return  # Command executed, stop checking
                except Exception as e:
                    logger.error(
                        f"Error executing custom command '{full_command}' "
                        f"in guild {message.guild.id}: {e}",
                        exc_info=True
                    )
                    # Don't send error to user, just log it
                    return

    async def _execute_command(self, message: discord.Message, cmd):
        """
        Execute a custom command

        Args:
            message: Discord message object
            cmd: CustomCommand entity
        """
        logger.info(
            f"Executing custom command '{cmd.get_full_command()}' "
            f"in guild {message.guild.name} (ID: {message.guild.id})"
        )

        try:
            if cmd.is_text_response():
                # Send text response
                await message.channel.send(cmd.response_text)

            elif cmd.is_embed_response():
                # Build and send embed
                embed = self.manager.build_embed_from_config(cmd.embed_config)
                await message.channel.send(embed=embed)

            else:
                logger.warning(
                    f"Unknown response type '{cmd.response_type}' "
                    f"for command {cmd.id}"
                )
                return

            # Increment use count asynchronously (don't wait)
            self.manager.increment_use_count(cmd.id)

        except discord.Forbidden:
            logger.warning(
                f"Missing permissions to send message in channel "
                f"{message.channel.id} (guild: {message.guild.id})"
            )
        except discord.HTTPException as e:
            logger.error(
                f"HTTP error executing command {cmd.id}: {e}",
                exc_info=True
            )
        except ValueError as e:
            # Invalid embed configuration
            logger.error(
                f"Invalid embed config for command {cmd.id}: {e}"
            )
            # Optionally notify guild admins that command has invalid config
            if message.guild.owner:
                try:
                    await message.guild.owner.send(
                        f"⚠️ Custom command `{cmd.get_full_command()}` in **{message.guild.name}** "
                        f"has an invalid embed configuration and cannot be executed. "
                        f"Please update or delete the command."
                    )
                except:
                    pass  # Can't DM owner, ignore

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        When bot joins a guild, pre-load custom commands into cache

        Args:
            guild: Discord guild object
        """
        logger.info(f"Pre-loading custom commands for new guild: {guild.name} (ID: {guild.id})")
        self.manager.get_guild_commands(guild.id, enabled_only=False, use_cache=False)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        When bot leaves a guild, clear cached commands

        Args:
            guild: Discord guild object
        """
        logger.info(f"Clearing custom command cache for removed guild: {guild.name} (ID: {guild.id})")
        self.manager.clear_cache(guild.id)


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(CustomCommands(bot))
