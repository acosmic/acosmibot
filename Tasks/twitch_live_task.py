import asyncio
import discord
import logging
import pytz
from datetime import datetime
from Services.twitch_service import TwitchService

logger = logging.getLogger(__name__)

# Track posted announcements per guild to prevent spam
_posted_announcements = {}


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await twitch_live_check_task(bot)


async def twitch_live_check_task(bot):
    """Monitor Twitch streamers and post announcements when they go live."""
    await bot.wait_until_ready()


    while not bot.is_closed():
        logger.info(f'Running twitch_live_check_task')

        try:
            await _check_all_guilds_twitch_streams(bot)
        except Exception as e:
            logger.error(f'Twitch live check task error: {e}')

        await asyncio.sleep(60)


async def _check_all_guilds_twitch_streams(bot):
    """Check Twitch streams for all guilds."""
    tw = TwitchService()

    for guild in bot.guilds:
        try:
            await _check_guild_twitch_streams(guild, tw)
        except Exception as e:
            logger.error(f'Error checking Twitch streams for guild {guild.name}: {e}')


async def _check_guild_twitch_streams(guild, tw):
    """Check Twitch streams for a specific guild."""
    # Get announcement channel for this guild
    announcement_channel = _get_twitch_announcement_channel(guild)

    if not announcement_channel:
        logger.debug(f'Guild {guild.name}: No Twitch announcement channel configured')
        return

    guild_id = guild.id

    # Initialize posted tracking for this guild if not exists
    if guild_id not in _posted_announcements:
        _posted_announcements[guild_id] = {}

    # Check tracked streamers for this guild
    tracked_streamers = _get_tracked_streamers_for_guild(guild)

    for streamer_username in tracked_streamers:
        try:
            await _check_streamer_status(
                streamer_username,
                guild,
                announcement_channel,
                tw
            )
        except Exception as e:
            logger.error(f'Guild {guild.name}: Error checking streamer {streamer_username}: {e}')


def _get_twitch_announcement_channel(guild):
    """Get the Twitch announcement channel for a guild."""
    # You can configure this per guild in various ways:

    # Option 1: Hardcoded channel names
    channel = discord.utils.get(guild.channels, name="twitch-announcements")
    if channel:
        return channel

    # Option 2: Look for channels with specific keywords
    for channel in guild.text_channels:
        if any(keyword in channel.name.lower() for keyword in ["twitch", "stream", "live"]):
            return channel

    # Option 3: Use a default channel (modify as needed)
    # You could store this in a database per guild
    channel_ids = {
        # Add your guild-specific channel IDs here
        # guild.id: channel_id
    }

    if guild.id in channel_ids:
        return guild.get_channel(channel_ids[guild.id])

    return None


def _get_tracked_streamers_for_guild(guild):
    """Get list of streamers to track for a specific guild."""
    # You can customize this per guild
    # For now, using the streamers from TwitchService
    tw = TwitchService()

    # Option 1: Use all streamers from the service
    streamers = list(tw.streamer_mapping.values())

    # Option 2: Guild-specific streamers (you could store this in database)
    guild_specific_streamers = {
        # guild.id: ["streamer1", "streamer2"]
    }

    if guild.id in guild_specific_streamers:
        return guild_specific_streamers[guild.id]

    # For now, just track "acosmic" for all guilds (modify as needed)
    return ["acosmic"]


async def _check_streamer_status(streamer_username, guild, channel, tw):
    """Check a specific streamer's status and handle announcements."""
    guild_id = guild.id

    try:
        is_live = tw.is_user_live(streamer_username)

        if is_live:
            # Check if we already posted for this streamer in this guild
            if not _posted_announcements[guild_id].get(streamer_username, False):
                await _post_live_announcement(streamer_username, guild, channel, tw)
                _posted_announcements[guild_id][streamer_username] = True
                logger.info(f'Guild {guild.name}: Posted Twitch announcement for {streamer_username}')
            else:
                logger.debug(f'Guild {guild.name}: {streamer_username} is live but announcement already posted')
        else:
            # Reset posted status when stream ends
            if _posted_announcements[guild_id].get(streamer_username, False):
                _posted_announcements[guild_id][streamer_username] = False
                logger.debug(f'Guild {guild.name}: {streamer_username} went offline, reset announcement status')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error checking {streamer_username}: {e}')


async def _post_live_announcement(streamer_username, guild, channel, tw):
    """Post a live announcement for a streamer."""
    try:
        # Get stream data
        stream_data = tw.get_stream_info(streamer_username)

        if not stream_data.get('data'):
            logger.warning(f'Guild {guild.name}: No stream data found for {streamer_username}')
            return

        stream_info = stream_data['data'][0]
        profile_picture = tw.get_user_profile_picture(streamer_username)

        # Extract stream information
        user_name = stream_info['user_name']
        game_name = stream_info['game_name']
        stream_title = stream_info['title']
        viewer_count = stream_info['viewer_count']
        stream_start_time = stream_info['started_at']
        thumbnail_url = stream_info['thumbnail_url'].format(width=1920, height=1080)

        # Create links
        stream_link = f"https://www.twitch.tv/{user_name}"
        markdown_link = f"[{stream_title}]({stream_link})"

        # Convert timestamp to Discord format
        discord_timestamp = _convert_to_discord_timestamp(stream_start_time)

        # Create embed
        embed = discord.Embed(
            title=f"🔴 {user_name} is live on Twitch!",
            description=f"## {markdown_link}",
            color=0x6441A4
        )
        embed.set_image(url=thumbnail_url)
        embed.set_thumbnail(url=profile_picture)
        embed.add_field(name="Category", value=game_name, inline=False)
        embed.add_field(name="Viewers", value=f"{viewer_count:,}", inline=False)
        embed.add_field(name="Started", value=discord_timestamp, inline=False)

        # Send announcement
        await channel.send(embed=embed)

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error posting announcement for {streamer_username}: {e}')


def _convert_to_discord_timestamp(stream_start_time):
    """Convert Twitch timestamp to Discord timestamp format."""
    try:
        # Parse the UTC timestamp
        dt = datetime.strptime(stream_start_time, "%Y-%m-%dT%H:%M:%SZ")
        dt_utc = dt.replace(tzinfo=pytz.utc)

        # Convert to Central Daylight Time (you can customize this per guild)
        cdt_timezone = pytz.timezone('America/Chicago')
        dt_cdt = dt_utc.astimezone(cdt_timezone)

        # Convert to Unix timestamp
        unix_timestamp = int(dt_cdt.timestamp())

        # Return Discord timestamp format
        return f"<t:{unix_timestamp}:F>"

    except Exception as e:
        logger.error(f'Error converting timestamp {stream_start_time}: {e}')
        return stream_start_time


# Utility function to manually reset announcement status (useful for testing)
def reset_announcement_status(guild_id=None, streamer_username=None):
    """Reset announcement status for debugging/testing."""
    global _posted_announcements

    if guild_id is None:
        _posted_announcements.clear()
        logger.info("Reset all announcement statuses")
    elif streamer_username is None:
        _posted_announcements[guild_id] = {}
        logger.info(f"Reset all announcement statuses for guild {guild_id}")
    else:
        if guild_id in _posted_announcements:
            _posted_announcements[guild_id][streamer_username] = False
            logger.info(f"Reset announcement status for {streamer_username} in guild {guild_id}")


# Configuration helper (you can expand this)
def configure_guild_streamers(guild_id, streamers):
    """Configure streamers to track for a specific guild."""
    # This would ideally be stored in a database
    # For now, you can extend the _get_tracked_streamers_for_guild function
    pass