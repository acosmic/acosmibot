#! /usr/bin/python3.10
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from typing import Optional, List, Annotated
import json

from Dao.CrossServerPortalDao import CrossServerPortalDao
from Dao.GuildDao import GuildDao
from Dao.UserDao import UserDao
from Entities.CrossServerPortal import CrossServerPortal
from logger import AppLogger


class PortalCommands(commands.Cog):
    """Commands for managing cross-server portals"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = AppLogger(__name__).get_logger()
        self.portal_dao = CrossServerPortalDao()
        self.guild_dao = GuildDao()
        self.user_dao = UserDao()

    def get_portal_settings(self, guild_id: int) -> dict:
        """Get portal settings for a guild from settings JSON"""
        settings = self.guild_dao.get_guild_settings(guild_id)
        if settings and 'cross_server_portal' in settings:
            return settings['cross_server_portal']

        # Return defaults if not configured
        return {
            'enabled': False,
            'channel_id': None,
            'public_listing': True,
            'display_name': None,
            'portal_cost': 1000
        }

    @app_commands.command(name="portal-search", description="Search for servers with portals enabled")
    @app_commands.describe(query="Server name to search for")
    async def portal_search(self, interaction: discord.Interaction, query: str):
        """Search for servers that have portals enabled and publicly listed"""
        await interaction.response.defer()

        try:
            # Get all guilds the bot is in
            all_guilds = self.guild_dao.get_all_guilds()

            matching_guilds = []
            for guild_entity in all_guilds:
                # Skip current guild
                if guild_entity.id == interaction.guild_id:
                    continue

                # Get portal settings
                portal_settings = self.get_portal_settings(guild_entity.id)

                # Check if portals are enabled and publicly listed
                if not portal_settings.get('enabled', False):
                    continue
                if not portal_settings.get('public_listing', True):
                    continue
                if portal_settings.get('channel_id') is None:
                    continue

                # Get display name
                display_name = portal_settings.get('display_name') or guild_entity.name

                # Check if query matches
                if query.lower() in display_name.lower():
                    matching_guilds.append({
                        'id': guild_entity.id,
                        'name': display_name,
                        'member_count': guild_entity.member_count,
                        'cost': portal_settings.get('portal_cost', 1000)
                    })

            if not matching_guilds:
                embed = discord.Embed(
                    title="🔍 No Portals Found",
                    description=f"No servers found matching '{query}' with portals enabled.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # Create embed with results
            embed = discord.Embed(
                title="🌀 Available Portals",
                description=f"Found {len(matching_guilds)} server(s) matching '{query}'",
                color=discord.Color.blue()
            )

            for guild_info in matching_guilds[:10]:  # Limit to 10 results
                embed.add_field(
                    name=f"{guild_info['name']}",
                    value=f"**ID:** `{guild_info['id']}`\n"
                          f"**Members:** {guild_info['member_count']}\n"
                          f"**Cost:** {guild_info['cost']} credits",
                    inline=False
                )

            if len(matching_guilds) > 10:
                embed.set_footer(text=f"Showing 10 of {len(matching_guilds)} results. Refine your search for more specific results.")

            embed.add_field(
                name="📝 How to Connect",
                value="Use `/portal-open <guild_id>` to open a portal!",
                inline=False
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error searching portals: {e}")
            await interaction.followup.send("An error occurred while searching for portals.", ephemeral=True)

    @app_commands.command(name="portal-open", description="Open a portal to another server (costs credits)")
    @app_commands.describe(target_guild_id="The ID of the server to connect to")
    async def portal_open(self, interaction: discord.Interaction, target_guild_id: str):
        """Open a 2-minute portal to another server"""
        await interaction.response.defer()

        try:
            # Validate permissions
            # if not interaction.user.guild_permissions.manage_guild:
            #     await interaction.followup.send("You need 'Manage Server' permission to open portals.", ephemeral=True)
            #     return

            # Parse target guild ID
            try:
                target_id = int(target_guild_id)
            except ValueError:
                await interaction.followup.send("Invalid guild ID. Please provide a numeric ID.", ephemeral=True)
                return

            # Check if portal already active in this guild
            existing_portal = self.portal_dao.get_active_portal_for_guild(interaction.guild_id)
            if existing_portal:
                await interaction.followup.send("A portal is already active in this server! Close it first with `/portal-close`.", ephemeral=True)
                return

            # Check if target guild has portals enabled
            target_guild_entity = self.guild_dao.get_guild(target_id)
            if not target_guild_entity:
                await interaction.followup.send("Target server not found or bot is not in that server.", ephemeral=True)
                return

            target_portal_settings = self.get_portal_settings(target_id)
            if not target_portal_settings.get('enabled', False):
                await interaction.followup.send("The target server does not have portals enabled.", ephemeral=True)
                return

            target_channel_id = target_portal_settings.get('channel_id')
            if not target_channel_id:
                await interaction.followup.send("The target server has not configured a portal channel.", ephemeral=True)
                return

            # Check if current guild has portals enabled
            source_portal_settings = self.get_portal_settings(interaction.guild_id)
            if not source_portal_settings.get('enabled', False):
                await interaction.followup.send("Portals are not enabled in this server. Ask an admin to enable them in the dashboard.", ephemeral=True)
                return

            source_channel_id = source_portal_settings.get('channel_id')
            if not source_channel_id:
                await interaction.followup.send("This server has not configured a portal channel. Ask an admin to set one up.", ephemeral=True)
                return

            # Check if user has enough credits
            user = self.user_dao.get_user(interaction.user.id)
            portal_cost = source_portal_settings.get('portal_cost', 1000)

            if not user or user.total_currency < portal_cost:
                await interaction.followup.send(f"You need {portal_cost} credits to open a portal. You have {user.total_currency if user else 0} credits.", ephemeral=True)
                return

            # Deduct credits
            user.total_currency -= portal_cost
            self.user_dao.update_user(user)

            # Create portal session
            now = datetime.now()
            closes_at = now + timedelta(minutes=2)

            portal = CrossServerPortal(
                guild_id_1=interaction.guild_id,
                guild_id_2=target_id,
                channel_id_1=int(source_channel_id),
                channel_id_2=int(target_channel_id),
                opened_by=interaction.user.id,
                cost_paid=portal_cost,
                opened_at=now,
                closes_at=closes_at,
                is_active=True
            )

            created_portal = self.portal_dao.create_portal(portal)
            if not created_portal:
                # Refund credits on failure
                user.total_currency += portal_cost
                self.user_dao.update_user(user)
                await interaction.followup.send("Failed to create portal. Credits have been refunded.", ephemeral=True)
                return

            # Get channels
            source_channel = self.bot.get_channel(int(source_channel_id))
            target_channel = self.bot.get_channel(int(target_channel_id))

            if not source_channel or not target_channel:
                self.portal_dao.close_portal(created_portal.id)
                user.total_currency += portal_cost
                self.user_dao.update_user(user)
                await interaction.followup.send("Could not access portal channels. Credits have been refunded.", ephemeral=True)
                return

            # Create portal embeds
            source_guild = interaction.guild
            target_guild = self.bot.get_guild(target_id)

            source_embed = discord.Embed(
                title="🌀 Portal Opened!",
                description=f"A portal to **{target_guild.name}** has been opened!\n\n"
                           f"**Duration:** 2 minutes\n"
                           f"**Message Limit:** 100 characters\n"
                           f"**Opened by:** {interaction.user.mention}\n\n"
                           f"Use `/portal-send` to send messages!\n"
                           f"🔵 = Your server  |  🟢 = {target_guild.name}",
                color=discord.Color.purple(),
                timestamp=closes_at
            )
            source_embed.set_footer(text="Portal closes at")
            source_embed.add_field(name="📝 Messages", value="*No messages yet*", inline=False)

            target_embed = discord.Embed(
                title="🌀 Portal Opened!",
                description=f"A portal from **{source_guild.name}** has been opened!\n\n"
                           f"**Duration:** 2 minutes\n"
                           f"**Message Limit:** 100 characters\n\n"
                           f"Use `/portal-send` to send messages!\n"
                           f"🔵 = Your server  |  🟢 = {source_guild.name}",
                color=discord.Color.purple(),
                timestamp=closes_at
            )
            target_embed.set_footer(text="Portal closes at")
            target_embed.add_field(name="📝 Messages", value="*No messages yet*", inline=False)

            # Send portal messages
            source_message = await source_channel.send(embed=source_embed)
            target_message = await target_channel.send(embed=target_embed)

            # Update portal with message IDs
            self.portal_dao.update_portal_messages(created_portal.id, source_message.id, target_message.id)

            # Send confirmation
            await interaction.followup.send(f"Portal opened successfully! {portal_cost} credits deducted. Portal will close in 2 minutes.")

        except Exception as e:
            self.logger.error(f"Error opening portal: {e}")
            await interaction.followup.send("An error occurred while opening the portal.", ephemeral=True)

    @app_commands.command(name="portal-close", description="Manually close an active portal")
    async def portal_close(self, interaction: discord.Interaction):
        """Manually close the active portal in this server"""
        await interaction.response.defer()

        try:
            # Check permissions
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.followup.send("You need 'Manage Server' permission to close portals.", ephemeral=True)
                return

            # Get active portal
            portal = self.portal_dao.get_active_portal_for_guild(interaction.guild_id)
            if not portal:
                await interaction.followup.send("No active portal found in this server.", ephemeral=True)
                return

            # Close portal
            self.portal_dao.close_portal(portal.id)

            # Update portal messages
            for guild_id, channel_id, message_id in [
                (portal.guild_id_1, portal.channel_id_1, portal.message_id_1),
                (portal.guild_id_2, portal.channel_id_2, portal.message_id_2)
            ]:
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel and message_id:
                        message = await channel.fetch_message(message_id)
                        embed = message.embeds[0]
                        embed.title = "🔒 Portal Closed"
                        embed.color = discord.Color.dark_gray()
                        embed.description = embed.description.replace("Portal Opened!", "Portal Closed!")
                        await message.edit(embed=embed)
                except Exception as e:
                    self.logger.error(f"Error updating portal message: {e}")

            await interaction.followup.send("Portal closed successfully!")

        except Exception as e:
            self.logger.error(f"Error closing portal: {e}")
            await interaction.followup.send("An error occurred while closing the portal.", ephemeral=True)

    @app_commands.command(name="portal-send", description="Send a message through the active portal")
    async def portal_send(
        self,
        interaction: discord.Interaction,
        message: Annotated[str, app_commands.Range[str, 1, 100]]
    ):
        """Send a message through an active portal"""
        # Defer without showing "thinking" spinner (portal processing can take >3 seconds)
        await interaction.response.defer(ephemeral=True, thinking=False)

        try:
            # Message length is enforced by Discord (1-100 characters)
            # No manual validation needed

            # Check if there's an active portal in this channel
            portal = self.portal_dao.get_active_portal_for_channel(interaction.channel_id)
            if not portal:
                await interaction.followup.send(
                    "No active portal in this channel. Use `/portal-open` to create one!",
                    ephemeral=True
                )
                return

            # Import the message listener to access its update methods
            from Cogs.PortalMessageListener import PortalMessageListener
            listener_cog = self.bot.get_cog('PortalMessageListener')

            if not listener_cog:
                await interaction.followup.send("Portal system not available.", ephemeral=True)
                return

            # Determine which guild this message is from
            username = interaction.user.display_name
            is_from_guild_1 = interaction.channel_id == portal.channel_id_1

            # Create two versions of the message with different colored indicators
            message_for_guild_1 = f"{'🔵' if is_from_guild_1 else '🟢'} [{username}]: {message}"
            message_for_guild_2 = f"{'🟢' if is_from_guild_1 else '🔵'} [{username}]: {message}"

            # Initialize cache if needed
            if portal.id not in listener_cog.portal_message_cache:
                listener_cog.portal_message_cache[portal.id] = {
                    'guild_1_messages': [],
                    'guild_2_messages': []
                }

            # Add messages to respective caches
            listener_cog.portal_message_cache[portal.id]['guild_1_messages'].append(message_for_guild_1)
            listener_cog.portal_message_cache[portal.id]['guild_2_messages'].append(message_for_guild_2)

            # Keep only last N messages for both views
            max_messages = listener_cog.MAX_MESSAGES_DISPLAYED
            if len(listener_cog.portal_message_cache[portal.id]['guild_1_messages']) > max_messages:
                listener_cog.portal_message_cache[portal.id]['guild_1_messages'] = \
                    listener_cog.portal_message_cache[portal.id]['guild_1_messages'][-max_messages:]

            if len(listener_cog.portal_message_cache[portal.id]['guild_2_messages']) > max_messages:
                listener_cog.portal_message_cache[portal.id]['guild_2_messages'] = \
                    listener_cog.portal_message_cache[portal.id]['guild_2_messages'][-max_messages:]

            # Update both portal messages
            await listener_cog.update_portal_messages(portal)

            await interaction.followup.send("message sent! :white_check_mark:", ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error sending portal message: {e}")
            await interaction.followup.send("An error occurred while sending your message.", ephemeral=True)

    @app_commands.command(name="portal-status", description="Check current portal status")
    async def portal_status(self, interaction: discord.Interaction):
        """Check the status of the current portal"""
        await interaction.response.defer(ephemeral=True)

        try:
            portal = self.portal_dao.get_active_portal_for_guild(interaction.guild_id)

            if not portal:
                await interaction.followup.send("No active portal in this server.", ephemeral=True)
                return

            # Calculate time remaining
            now = datetime.now()
            if isinstance(portal.closes_at, str):
                closes_at = datetime.fromisoformat(portal.closes_at)
            else:
                closes_at = portal.closes_at

            time_remaining = closes_at - now
            seconds_remaining = int(time_remaining.total_seconds())

            # Get connected guild info
            other_guild_id = portal.guild_id_2 if portal.guild_id_1 == interaction.guild_id else portal.guild_id_1
            other_guild = self.bot.get_guild(other_guild_id)
            other_guild_name = other_guild.name if other_guild else f"Unknown Server ({other_guild_id})"

            embed = discord.Embed(
                title="🌀 Portal Status",
                description=f"Connected to: **{other_guild_name}**",
                color=discord.Color.purple()
            )
            embed.add_field(name="Time Remaining", value=f"{seconds_remaining} seconds", inline=True)
            embed.add_field(name="Opened By", value=f"<@{portal.opened_by}>", inline=True)
            embed.add_field(name="Cost Paid", value=f"{portal.cost_paid} credits", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error checking portal status: {e}")
            await interaction.followup.send("An error occurred while checking portal status.", ephemeral=True)


async def setup(bot):
    """Set up the cog"""
    await bot.add_cog(PortalCommands(bot))
