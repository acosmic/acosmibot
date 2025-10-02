import asyncio
import discord
import logging
import pytz
from datetime import datetime
from Services.twitch_service import TwitchService
import aiohttp

logger = logging.getLogger(__name__)

# Track posted announcements per guild to prevent spam
_posted_announcements = {}
_announcements_lock = asyncio.Lock()  # async-safe tracking


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
            logger.error(f'Twitch live check task error: {e}', exc_info=True)

        await asyncio.sleep(60)


async def _check_all_guilds_twitch_streams(bot):
    """Check Twitch streams for all guilds."""
    tw = TwitchService()

    tasks = []
    for guild in bot.guilds:
        tasks.append(_check_guild_twitch_streams(guild, tw))

    await asyncio.gather(*tasks, return_exceptions=True)


async def _check_guild_twitch_streams(guild, tw):
    """Check Twitch streams for a specific guild."""
    announcement_channel = _get_twitch_announcement_channel(guild)

    if not announcement_channel:
        logger.debug(f'Guild {guild.name}: No Twitch announcement channel configured')
        return

    guild_id = guild.id

    async with _announcements_lock:
        if guild_id not in _posted_announcements:
            _posted_announcements[guild_id] = {}

    tracked_streamers = _get_tracked_streamers_for_guild(guild)

    tasks = [
        _check_streamer_status(streamer_username, guild, announcement_channel, tw)
        for streamer_username in tracked_streamers
    ]
    await asyncio.gather(*tasks, return_exceptions=True)


def _get_twitch_announcement_channel(guild):
    """Get the Twitch announcement channel for a guild."""
    # Option 1: Hardcoded channel name
    channel = discord.utils.get(guild.channels, name="twitch-announcements")
    if channel:
        return channel

    # Option 2: Keyword search
    for channel in guild.text_channels:
        if any(keyword in channel.name.lower() for keyword in ["twitch", "stream", "live"]):
            return channel

    # Option 3: Fallback to system channel
    if guild.system_channel:
        return guild.system_channel

    return None


def _get_tracked_streamers_for_guild(guild):
    """Get list of streamers to track for a specific guild."""
    tw = TwitchService()
    streamers = list(tw.streamer_mapping.values())

    # Guild-specific streamers could be stored in DB
    guild_specific_streamers = {
        # guild.id: ["streamer1", "streamer2"]
    }

    if guild.id in guild_specific_streamers:
        return guild_specific_streamers[guild.id]

    # Default fallback
    return ["acosmic"]


async def _check_streamer_status(streamer_username, guild, channel, tw):
    """Check a specific streamer's status and handle announcements."""
    guild_id = guild.id

    try:
        # Create aiohttp session for API calls
        async with aiohttp.ClientSession() as session:
            is_live = await tw.is_user_live(session, streamer_username)

            async with _announcements_lock:
                already_posted = _posted_announcements[guild_id].get(streamer_username, False)

            if is_live:
                if not already_posted:
                    await _post_live_announcement(streamer_username, guild, channel, tw, session)
                    async with _announcements_lock:
                        _posted_announcements[guild_id][streamer_username] = True
                    logger.info(f'Guild {guild.name}: Posted Twitch announcement for {streamer_username}')
                else:
                    logger.debug(f'Guild {guild.name}: {streamer_username} is live but announcement already posted')
            else:
                if already_posted:
                    async with _announcements_lock:
                        _posted_announcements[guild_id][streamer_username] = False
                    logger.debug(f'Guild {guild.name}: {streamer_username} went offline, reset announcement status')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error checking {streamer_username}: {e}', exc_info=True)


async def _post_live_announcement(streamer_username, guild, channel, tw, session):
    """Post a live announcement for a streamer."""
    try:
        stream_data = await tw.get_stream_info(session, streamer_username)

        if not stream_data.get('data'):
            logger.warning(f'Guild {guild.name}: No stream data found for {streamer_username}')
            return

        stream_info = stream_data['data'][0]
        profile_picture = await tw.get_user_info(session, streamer_username)

        # Extract profile picture URL from user info
        profile_picture_url = profile_picture.get('profile_image_url', '') if profile_picture else ''


        user_name = stream_info['user_name']
        game_name = stream_info['game_name']
        stream_title = stream_info['title']
        viewer_count = stream_info['viewer_count']
        stream_start_time = stream_info['started_at']
        thumbnail_url = stream_info['thumbnail_url'].format(width=1920, height=1080)

        stream_link = f"https://www.twitch.tv/{user_name}"
        markdown_link = f"[{stream_title}]({stream_link})"

        discord_timestamp = _convert_to_discord_timestamp(stream_start_time)

        embed = discord.Embed(
            title=f"🔴 {user_name} is live on Twitch!",
            description=f"## {markdown_link}",
            color=0x6441A4
        )
        embed.set_image(url=thumbnail_url)
        embed.set_thumbnail(url=profile_picture_url)
        embed.add_field(name="Category", value=game_name, inline=False)
        embed.add_field(name="Viewers", value=f"{viewer_count:,}", inline=False)
        embed.add_field(name="Started", value=discord_timestamp, inline=False)

        await channel.send(embed=embed)

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error posting announcement for {streamer_username}: {e}', exc_info=True)


def _convert_to_discord_timestamp(stream_start_time):
    """Convert Twitch timestamp to Discord timestamp format."""
    try:
        dt = datetime.strptime(stream_start_time, "%Y-%m-%dT%H:%M:%SZ")
        dt_utc = dt.replace(tzinfo=pytz.utc)
        cdt_timezone = pytz.timezone('America/Chicago')
        dt_cdt = dt_utc.astimezone(cdt_timezone)
        unix_timestamp = int(dt_cdt.timestamp())
        return f"<t:{unix_timestamp}:F>"
    except Exception as e:
        logger.error(f'Error converting timestamp {stream_start_time}: {e}', exc_info=True)
        return stream_start_time


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


def configure_guild_streamers(guild_id, streamers):
    """Configure streamers to track for a specific guild."""
    # Would ideally store this in a DB
    pass
