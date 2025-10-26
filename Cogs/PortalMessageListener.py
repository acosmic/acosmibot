#! /usr/bin/python3.10
import discord
from discord.ext import commands
from datetime import datetime
from typing import Dict, List
import asyncio

from Dao.CrossServerPortalDao import CrossServerPortalDao
from logger import AppLogger


class PortalMessageListener(commands.Cog):
    """Listener for relaying messages through active portals"""

    MAX_MESSAGE_LENGTH = 100
    MAX_MESSAGES_DISPLAYED = 20  # Keep last 20 messages in the chat log

    def __init__(self, bot):
        self.bot = bot
        self.logger = AppLogger(__name__).get_logger()
        self.portal_dao = CrossServerPortalDao()
        # Cache of portal messages with separate views for each guild
        # {portal_id: {'guild_1_messages': [...], 'guild_2_messages': [...]}}
        self.portal_message_cache: Dict[int, Dict[str, List[str]]] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Portal messages are now sent via /portal-send command.
        This listener is disabled to prevent rate limiting issues.
        """
        # Portal messaging is now handled by the /portal-send command
        # to avoid Discord API rate limiting from rapid message edits
        pass

    async def update_portal_messages(self, portal):
        """Update both portal embed messages with the latest chat log"""
        try:
            # Get message cache
            cache = self.portal_message_cache.get(portal.id, {'guild_1_messages': [], 'guild_2_messages': []})

            # Calculate time remaining
            now = datetime.now()
            if isinstance(portal.closes_at, str):
                closes_at = datetime.fromisoformat(portal.closes_at)
            else:
                closes_at = portal.closes_at

            time_remaining = closes_at - now
            seconds_remaining = max(0, int(time_remaining.total_seconds()))

            # Update both messages with their respective views
            for channel_id, message_id, guild_id in [
                (portal.channel_id_1, portal.message_id_1, portal.guild_id_1),
                (portal.channel_id_2, portal.message_id_2, portal.guild_id_2)
            ]:
                try:
                    channel = self.bot.get_channel(channel_id)
                    if not channel or not message_id:
                        continue

                    message = await channel.fetch_message(message_id)
                    embed = message.embeds[0]

                    # Get the appropriate message list for this guild
                    is_guild_1 = guild_id == portal.guild_id_1
                    messages = cache['guild_1_messages'] if is_guild_1 else cache['guild_2_messages']
                    messages_text = "\n".join(messages) if messages else "*No messages yet*"

                    # Get the other guild name
                    other_guild_id = portal.guild_id_2 if is_guild_1 else portal.guild_id_1
                    other_guild = self.bot.get_guild(other_guild_id)
                    other_guild_name = other_guild.name if other_guild else "Unknown Server"

                    # Update embed
                    embed.description = (
                        f"A portal to **{other_guild_name}** is open!\n\n"
                        f"**Time Remaining:** {seconds_remaining}s\n"
                        f"**Message Limit:** {self.MAX_MESSAGE_LENGTH} characters\n\n"
                        f"Use `/portal-send` to send messages!\n"
                        f"🔵 = Your server  |  🟢 = {other_guild_name}"
                    )

                    # Update messages field
                    if len(messages_text) > 1024:
                        # Discord field value limit is 1024 characters
                        messages_text = "...\n" + messages_text[-(1024-4):]

                    embed.set_field_at(0, name="📝 Messages", value=messages_text, inline=False)

                    await message.edit(embed=embed)

                except discord.NotFound:
                    self.logger.warning(f"Portal message not found: {message_id}")
                except Exception as e:
                    self.logger.error(f"Error updating portal message: {e}")

        except Exception as e:
            self.logger.error(f"Error in update_portal_messages: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize portal message cache on startup"""
        try:
            # Clear any stale caches
            self.portal_message_cache.clear()
            self.logger.info("Portal message listener ready")
        except Exception as e:
            self.logger.error(f"Error initializing portal message listener: {e}")


async def setup(bot):
    """Set up the cog"""
    await bot.add_cog(PortalMessageListener(bot))
