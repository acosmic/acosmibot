#! /usr/bin/python3.10
import discord
from discord.ext import commands
from discord import app_commands
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class ActivityDiagnostic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="check-activities", description="Check a user's current Discord activities (Admin only)")
    @app_commands.describe(user="The user to check activities for")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def check_activities(self, interaction: discord.Interaction, user: discord.Member):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Get member from cache (includes presence data from gateway)
            cached_member = interaction.guild.get_member(user.id)
            if not cached_member:
                await interaction.followup.send(f"User {user.mention} not found in member cache.", ephemeral=True)
                return

            # Also fetch from REST API for comparison
            fetched_member = await interaction.guild.fetch_member(user.id)

            # Build embed with activity information
            embed = discord.Embed(
                title=f"Activity Diagnostic for {cached_member.display_name}",
                description=f"User ID: {cached_member.id}\n\n**Comparing cached (gateway) vs fetched (REST API) data:**",
                color=discord.Color.blue()
            )

            # Show both statuses for comparison
            embed.add_field(
                name="📊 Status Comparison",
                value=f"**Cached (with presence):** {cached_member.status}\n**Fetched (REST API):** {fetched_member.status}",
                inline=False
            )

            # Platform-specific statuses (from cached member only - not available via REST)
            if hasattr(cached_member, 'desktop_status'):
                embed.add_field(name="Desktop Status", value=str(cached_member.desktop_status), inline=True)
            if hasattr(cached_member, 'mobile_status'):
                embed.add_field(name="Mobile Status", value=str(cached_member.mobile_status), inline=True)
            if hasattr(cached_member, 'web_status'):
                embed.add_field(name="Web Status", value=str(cached_member.web_status), inline=True)

            # Activity count comparison
            cached_count = len(cached_member.activities)
            fetched_count = len(fetched_member.activities)
            embed.add_field(
                name="🎮 Activity Count",
                value=f"**Cached:** {cached_count}\n**Fetched:** {fetched_count}",
                inline=False
            )

            # Detailed activity breakdown (use cached member which has presence data)
            if cached_member.activities:
                for i, activity in enumerate(cached_member.activities):
                    activity_info = []
                    activity_info.append(f"**Class Type:** {type(activity).__name__}")

                    if hasattr(activity, 'name'):
                        activity_info.append(f"**Name:** {activity.name}")
                    if hasattr(activity, 'type'):
                        activity_info.append(f"**Type:** {activity.type}")
                    if hasattr(activity, 'url'):
                        activity_info.append(f"**URL:** {activity.url}")
                    if hasattr(activity, 'platform'):
                        activity_info.append(f"**Platform:** {activity.platform}")
                    if hasattr(activity, 'details'):
                        activity_info.append(f"**Details:** {activity.details}")
                    if hasattr(activity, 'state'):
                        activity_info.append(f"**State:** {activity.state}")

                    # Check if it's a streaming activity
                    is_streaming = isinstance(activity, discord.Streaming)
                    activity_info.append(f"**Is Streaming Type:** {is_streaming}")

                    if hasattr(activity, 'type'):
                        is_streaming_enum = activity.type == discord.ActivityType.streaming
                        activity_info.append(f"**Type == ActivityType.streaming:** {is_streaming_enum}")

                    embed.add_field(
                        name=f"Activity [{i}]",
                        value="\n".join(activity_info),
                        inline=False
                    )
            else:
                embed.add_field(name="Activities", value="No activities detected", inline=False)

            # Check streaming activities
            streaming_activities = [
                activity for activity in cached_member.activities
                if isinstance(activity, discord.Streaming)
            ]
            embed.add_field(
                name="🎥 Streaming Activities Found",
                value=str(len(streaming_activities)),
                inline=False
            )

            # Add interpretation
            if cached_count > 0 and fetched_count == 0:
                embed.add_field(
                    name="✅ Result",
                    value="**Presence Intent is WORKING!**\nCached data has activities, fetched data doesn't.\nThis is expected behavior.",
                    inline=False
                )
            elif cached_count == 0 and fetched_count == 0:
                embed.add_field(
                    name="⚠️ Result",
                    value="**No activities detected in either method.**\nUser may have no activities, or Presence Intent may not be working.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="ℹ️ Result",
                    value=f"Cached: {cached_count} activities, Fetched: {fetched_count} activities",
                    inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Activity diagnostic run by {interaction.user.display_name} for user {cached_member.display_name} (ID: {cached_member.id})")

        except discord.NotFound:
            await interaction.followup.send(f"User with ID {user.id} not found in this server.", ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"HTTP error checking activities for {user.id}: {e}")
            await interaction.followup.send(f"Failed to fetch user data: {e}", ephemeral=True)
        except Exception as e:
            logger.error(f"Unexpected error checking activities for {user.id}: {e}")
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ActivityDiagnostic(bot))
