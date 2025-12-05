#! /usr/bin/python3.10
"""
Unified multi-platform streaming live task

Monitors Twitch and YouTube streamers and posts announcements when they go live.
Supports platform-specific limits, features, and VOD tracking.
"""
import asyncio
import discord
import logging
import pytz
from datetime import datetime
from Services.twitch_service import TwitchService
from Services.youtube_service import YouTubeService
from Dao.GuildDao import GuildDao
from Dao.StreamingAnnouncementDao import StreamingAnnouncementDao
import aiohttp

logger = logging.getLogger(__name__)

# Track posted announcements per guild to prevent spam
# Structure: {guild_id: {'twitch': {username: bool}, 'youtube': {username: bool}}}
_posted_announcements = {}
_announcements_lock = asyncio.Lock()


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await unified_streaming_live_check_task(bot)


async def _initialize_announcement_cache(bot):
    """
    Initialize the announcement cache from database on startup.

    This prevents duplicate announcements after bot restarts by loading
    currently active streams from the database for both platforms.
    """
    dao = StreamingAnnouncementDao()

    try:
        # Load Twitch active streams
        twitch_active = dao.get_active_announcements_for_cache('twitch')
        youtube_active = dao.get_active_announcements_for_cache('youtube')

        async with _announcements_lock:
            for announcement in twitch_active:
                guild_id = announcement.guild_id
                username = announcement.streamer_username

                if guild_id not in _posted_announcements:
                    _posted_announcements[guild_id] = {'twitch': {}, 'youtube': {}}
                if 'twitch' not in _posted_announcements[guild_id]:
                    _posted_announcements[guild_id]['twitch'] = {}

                _posted_announcements[guild_id]['twitch'][username] = True

            for announcement in youtube_active:
                guild_id = announcement.guild_id
                username = announcement.streamer_username

                if guild_id not in _posted_announcements:
                    _posted_announcements[guild_id] = {'twitch': {}, 'youtube': {}}
                if 'youtube' not in _posted_announcements[guild_id]:
                    _posted_announcements[guild_id]['youtube'] = {}

                _posted_announcements[guild_id]['youtube'][username] = True

        total_active = len(twitch_active) + len(youtube_active)
        logger.info(
            f"Initialized streaming announcement cache with {total_active} active streams "
            f"({len(twitch_active)} Twitch, {len(youtube_active)} YouTube)"
        )
    except Exception as e:
        logger.error(f"Error initializing streaming announcement cache: {e}", exc_info=True)
    finally:
        dao.close()


async def unified_streaming_live_check_task(bot):
    """Monitor Twitch and YouTube streamers and post announcements when they go live."""
    await bot.wait_until_ready()

    # Initialize cache from database on startup
    await _initialize_announcement_cache(bot)

    while not bot.is_closed():
        logger.debug('Running unified_streaming_live_check_task')

        try:
            await _check_all_guilds_streams(bot)

            # Also check for streams that need 20-minute status updates
            await _check_stream_status_updates(bot)
        except Exception as e:
            logger.error(f'Unified streaming live check task error: {e}', exc_info=True)

        await asyncio.sleep(60)


async def _check_all_guilds_streams(bot):
    """Check streams for all guilds (both Twitch and YouTube)."""
    twitch_service = TwitchService()
    youtube_service = YouTubeService()

    tasks = []
    for guild in bot.guilds:
        tasks.append(_check_guild_streams(guild, twitch_service, youtube_service))

    await asyncio.gather(*tasks, return_exceptions=True)


async def _check_guild_streams(guild, twitch_service, youtube_service):
    """Check streams for a specific guild (both platforms)."""
    guild_dao = GuildDao()
    try:
        settings = guild_dao.get_guild_settings(guild.id)
        streaming_settings = settings.get('streaming', {})

        # Check if streaming notifications are enabled
        if not streaming_settings.get('enabled'):
            return

        # Get announcement channel
        channel_id = streaming_settings.get('announcement_channel_id')
        if not channel_id:
            logger.debug(f'Guild {guild.name}: Streaming enabled but no announcement channel configured')
            return

        channel = guild.get_channel(int(channel_id))
        if not channel:
            logger.warning(f'Guild {guild.name}: Streaming announcement channel {channel_id} not found')
            return

        # Get tracked streamers
        tracked_streamers = streaming_settings.get('tracked_streamers', [])
        if not tracked_streamers:
            logger.debug(f'Guild {guild.name}: No streamers configured')
            return

        guild_id = guild.id

        async with _announcements_lock:
            if guild_id not in _posted_announcements:
                _posted_announcements[guild_id] = {'twitch': {}, 'youtube': {}}

        # Check each streamer in parallel
        tasks = []
        for streamer_config in tracked_streamers:
            platform = streamer_config.get('platform')
            username = streamer_config.get('username')

            if not platform or not username:
                logger.warning(f'Guild {guild.name}: Streamer config missing platform or username')
                continue

            if platform == 'twitch':
                tasks.append(_check_twitch_streamer(
                    username,
                    streamer_config,
                    guild,
                    channel,
                    twitch_service,
                    streaming_settings
                ))
            elif platform == 'youtube':
                tasks.append(_check_youtube_streamer(
                    username,
                    streamer_config,
                    guild,
                    channel,
                    youtube_service,
                    streaming_settings
                ))
            else:
                logger.warning(f'Guild {guild.name}: Unknown platform {platform} for streamer {username}')

        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        guild_dao.close()


async def _check_twitch_streamer(username, streamer_config, guild, channel, tw, settings):
    """Check a specific Twitch streamer's status and handle announcements."""
    guild_id = guild.id
    platform = 'twitch'

    try:
        async with aiohttp.ClientSession() as session:
            is_live = await tw.is_user_live(session, username)

            async with _announcements_lock:
                already_posted = _posted_announcements[guild_id][platform].get(username, False)

            if is_live:
                if not already_posted:
                    await _post_twitch_live_announcement(
                        username,
                        streamer_config,
                        guild,
                        channel,
                        tw,
                        session,
                        settings
                    )
                    async with _announcements_lock:
                        _posted_announcements[guild_id][platform][username] = True
                    logger.info(f'Guild {guild.name}: Posted Twitch announcement for {username}')
                else:
                    logger.debug(f'Guild {guild.name}: {username} is live but announcement already posted')
            else:
                if already_posted:
                    # Stream went offline - edit the embed and mark offline
                    await _handle_stream_offline(
                        guild, guild_id, username, platform, tw, session
                    )
                    async with _announcements_lock:
                        _posted_announcements[guild_id][platform][username] = False
                    logger.debug(f'Guild {guild.name}: {username} went offline, edited announcement')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error checking Twitch {username}: {e}', exc_info=True)


async def _check_youtube_streamer(username, streamer_config, guild, channel, yt, settings):
    """Check a specific YouTube streamer's status and handle announcements."""
    guild_id = guild.id
    platform = 'youtube'

    try:
        async with aiohttp.ClientSession() as session:
            # Resolve channel ID (cached in streamer_config ideally)
            channel_id = streamer_config.get('streamer_id')
            if not channel_id:
                channel_id = await yt.resolve_channel_id(session, username)
                if not channel_id:
                    logger.warning(f'Guild {guild.name}: Could not resolve YouTube channel for {username}')
                    return

            # Check if live
            stream_data = await yt.get_live_stream_info(session, channel_id)
            is_live = stream_data is not None

            async with _announcements_lock:
                already_posted = _posted_announcements[guild_id][platform].get(username, False)

            if is_live:
                if not already_posted:
                    await _post_youtube_live_announcement(
                        username,
                        streamer_config,
                        channel_id,
                        stream_data,
                        guild,
                        channel,
                        yt,
                        session,
                        settings
                    )
                    async with _announcements_lock:
                        _posted_announcements[guild_id][platform][username] = True
                    logger.info(f'Guild {guild.name}: Posted YouTube announcement for {username}')
                else:
                    logger.debug(f'Guild {guild.name}: {username} is live but announcement already posted')
            else:
                if already_posted:
                    # Stream went offline
                    await _handle_stream_offline(
                        guild, guild_id, username, platform, yt, session, channel_id=channel_id
                    )
                    async with _announcements_lock:
                        _posted_announcements[guild_id][platform][username] = False
                    logger.debug(f'Guild {guild.name}: {username} went offline, edited announcement')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error checking YouTube {username}: {e}', exc_info=True)


async def _post_twitch_live_announcement(username, streamer_config, guild, channel, tw, session, settings):
    """Post a live announcement for a Twitch streamer."""
    try:
        stream_data = await tw.get_stream_info(session, username)

        if not stream_data.get('data'):
            logger.warning(f'Guild {guild.name}: No stream data found for {username}')
            return

        stream_info = stream_data['data'][0]
        profile_picture = await tw.get_user_info(session, username)
        profile_picture_url = profile_picture.get('profile_image_url', '') if profile_picture else ''

        # Extract stream data
        user_name = stream_info['user_name']
        game_name = stream_info['game_name']
        stream_title = stream_info['title']
        viewer_count = stream_info['viewer_count']
        stream_start_time = stream_info['started_at']
        thumbnail_url = stream_info['thumbnail_url'].format(width=1920, height=1080)
        stream_link = f"https://www.twitch.tv/{user_name}"

        # Get announcement settings
        ann_settings = settings.get('announcement_settings', {})
        color_hex = ann_settings.get('twitch_color', '0x6441A4')
        color = int(color_hex.replace('0x', ''), 16) if isinstance(color_hex, str) else color_hex

        # Build embed
        embed_title = f"🔴 {user_name} is live on Twitch!"
        markdown_link = f"[{stream_title}]({stream_link})"

        embed = discord.Embed(
            title=embed_title,
            description=f"## {markdown_link}",
            color=color
        )

        # Add embed fields based on settings
        if ann_settings.get('include_thumbnail', True):
            embed.set_image(url=thumbnail_url)
            embed.set_thumbnail(url=profile_picture_url)

        if ann_settings.get('include_game', True):
            embed.add_field(name="Category", value=game_name, inline=False)

        if ann_settings.get('include_viewer_count', True):
            embed.add_field(name="Viewers", value=f"{viewer_count:,}", inline=False)

        if ann_settings.get('include_start_time', True):
            discord_timestamp = _convert_to_discord_timestamp(stream_start_time)
            embed.add_field(name="Started", value=discord_timestamp, inline=False)

        # Build content with pings and custom message
        content = _build_announcement_content(streamer_config, user_name, game_name, stream_title, viewer_count)

        # Send message
        message = await channel.send(content=content, embed=embed)

        # Store in database for VOD tracking
        dao = StreamingAnnouncementDao()
        try:
            stream_started_dt = datetime.strptime(stream_start_time, "%Y-%m-%dT%H:%M:%SZ")
            dao.create_announcement(
                platform='twitch',
                guild_id=guild.id,
                channel_id=channel.id,
                message_id=message.id,
                streamer_username=username,
                streamer_id=None,  # Twitch doesn't need this cached
                stream_id=None,
                stream_title=stream_title,
                game_name=game_name,
                stream_started_at=stream_started_dt,
                initial_viewer_count=viewer_count
            )
            logger.info(f'Guild {guild.name}: Posted Twitch announcement for {username} (message {message.id})')
        finally:
            dao.close()

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error posting Twitch announcement for {username}: {e}', exc_info=True)


async def _post_youtube_live_announcement(
    username, streamer_config, channel_id, stream_data, guild, channel, yt, session, settings
):
    """Post a live announcement for a YouTube streamer."""
    try:
        # Extract stream data
        video_id = stream_data['video_id']
        stream_title = stream_data['title']
        channel_title = stream_data['channel_title']
        viewer_count = stream_data['viewer_count']
        thumbnail_url = stream_data['thumbnail_url']
        stream_url = stream_data['url']
        started_at = stream_data['started_at']  # ISO 8601 format

        # Get channel info for avatar
        channel_info = await yt.get_channel_info(session, channel_id)
        channel_thumbnail = channel_info.get('thumbnail_url', '') if channel_info else ''

        # Get announcement settings
        ann_settings = settings.get('announcement_settings', {})
        color_hex = ann_settings.get('youtube_color', '0xFF0000')
        color = int(color_hex.replace('0x', ''), 16) if isinstance(color_hex, str) else color_hex

        # Build embed
        embed_title = f"🔴 {channel_title} is live on YouTube!"
        markdown_link = f"[{stream_title}]({stream_url})"

        embed = discord.Embed(
            title=embed_title,
            description=f"## {markdown_link}",
            color=color
        )

        # Add embed fields based on settings
        if ann_settings.get('include_thumbnail', True):
            embed.set_image(url=thumbnail_url)
            embed.set_thumbnail(url=channel_thumbnail)

        # YouTube uses category ID, not name - skip for now or map later
        # if ann_settings.get('include_game', True):
        #     embed.add_field(name="Category", value="...", inline=False)

        if ann_settings.get('include_viewer_count', True):
            embed.add_field(name="Viewers", value=f"{viewer_count:,}", inline=False)

        if ann_settings.get('include_start_time', True):
            discord_timestamp = _convert_to_discord_timestamp(started_at)
            embed.add_field(name="Started", value=discord_timestamp, inline=False)

        # Build content with pings and custom message
        content = _build_announcement_content(streamer_config, channel_title, "", stream_title, viewer_count)

        # Send message
        message = await channel.send(content=content, embed=embed)

        # Store in database for VOD tracking
        dao = StreamingAnnouncementDao()
        try:
            # Parse ISO 8601 timestamp
            try:
                stream_started_dt = datetime.strptime(started_at, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                # Try with fractional seconds
                stream_started_dt = datetime.strptime(started_at.split('.')[0], "%Y-%m-%dT%H:%M:%S")

            dao.create_announcement(
                platform='youtube',
                guild_id=guild.id,
                channel_id=channel.id,
                message_id=message.id,
                streamer_username=username,
                streamer_id=channel_id,  # Cache resolved channel ID
                stream_id=video_id,  # Important for VOD detection
                stream_title=stream_title,
                game_name=None,  # YouTube doesn't provide category name easily
                stream_started_at=stream_started_dt,
                initial_viewer_count=viewer_count
            )
            logger.info(f'Guild {guild.name}: Posted YouTube announcement for {username} (message {message.id})')
        finally:
            dao.close()

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error posting YouTube announcement for {username}: {e}', exc_info=True)


def _build_announcement_content(streamer_config, username, game_name, stream_title, viewer_count):
    """Build announcement content with mentions and custom message."""
    mention_parts = []

    # Add role mentions
    if streamer_config.get('mention_role_ids'):
        role_ids = streamer_config['mention_role_ids']
        if isinstance(role_ids, list):
            for role_id in role_ids:
                mention_parts.append(f"<@&{role_id}>")
        else:
            mention_parts.append(f"<@&{role_ids}>")

    # Add @everyone
    if streamer_config.get('mention_everyone'):
        mention_parts.append("@everyone")

    # Add @here
    if streamer_config.get('mention_here'):
        mention_parts.append("@here")

    # Build final content
    content_parts = []

    # Add pings first
    if mention_parts:
        content_parts.append(" ".join(mention_parts))

    # Add custom message if configured
    custom_message = streamer_config.get('custom_message')
    if custom_message:
        # Replace placeholders
        custom_message = custom_message.replace('{username}', username)
        custom_message = custom_message.replace('{game}', game_name)
        custom_message = custom_message.replace('{title}', stream_title)
        custom_message = custom_message.replace('{viewer_count}', str(viewer_count))
        content_parts.append(custom_message)

    # Combine content (pings + custom message) or None
    return " ".join(content_parts) if content_parts else None


async def _handle_stream_offline(guild, guild_id, username, platform, service, session, channel_id=None):
    """Handle stream going offline - edit embed and mark in database."""
    dao = StreamingAnnouncementDao()
    try:
        # Fetch the announcement from database
        announcement = dao.get_active_stream_for_streamer(platform, guild_id, username)

        if not announcement:
            logger.warning(f'Guild {guild.name}: No active announcement found for {platform} {username}')
            return

        # Calculate stream duration
        stream_end_time = datetime.utcnow()
        duration_seconds = int((stream_end_time - announcement.stream_started_at).total_seconds())

        # Try to get final viewer count
        final_viewer_count = None
        try:
            if platform == 'twitch':
                stream_data = await service.get_stream_info(session, username)
                if stream_data.get('data') and len(stream_data['data']) > 0:
                    final_viewer_count = stream_data['data'][0].get('viewer_count')
            elif platform == 'youtube' and channel_id:
                stream_data = await service.get_live_stream_info(session, channel_id)
                if stream_data:
                    final_viewer_count = stream_data.get('viewer_count')
        except Exception as e:
            logger.debug(f'Guild {guild.name}: Could not fetch final viewer count: {e}')

        # Edit the announcement message
        await _edit_announcement_on_stream_end(
            guild,
            announcement.channel_id,
            announcement.message_id,
            announcement.stream_started_at,
            stream_end_time,
            duration_seconds,
            final_viewer_count
        )

        # Update database with end info
        dao.mark_stream_offline(
            platform,
            guild_id,
            username,
            stream_end_time,
            final_viewer_count
        )

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error handling offline stream: {e}', exc_info=True)
    finally:
        dao.close()


async def _edit_announcement_on_stream_end(
    guild,
    channel_id: int,
    message_id: int,
    stream_started_at: datetime,
    stream_end_time: datetime,
    duration_seconds: int,
    final_viewer_count: int = None
):
    """Edit announcement embed when stream ends with timing and viewer info."""
    try:
        channel = guild.get_channel(channel_id)
        if not channel:
            logger.warning(f'Guild {guild.name}: Channel {channel_id} not found for editing announcement')
            return

        message = await channel.fetch_message(message_id)
        if not message or not message.embeds:
            logger.warning(f'Guild {guild.name}: Message {message_id} or embeds not found')
            return

        embed = message.embeds[0]

        # Update title: Change from "is live" to "was live"
        if "is live" in embed.title:
            embed.title = embed.title.replace("🔴 ", "📹 ").replace("is live", "was live")

        # Remove image preview
        embed.set_image(url=None)

        # Update color to gray for ended stream
        embed.color = 0x808080

        # Convert timestamps to Discord format
        started_ts = int(stream_started_at.replace(tzinfo=pytz.utc).timestamp())
        ended_ts = int(stream_end_time.replace(tzinfo=pytz.utc).timestamp())

        # Add stream end metadata fields
        embed.add_field(name="Ended", value=f"<t:{ended_ts}:F>", inline=False)
        embed.add_field(name="Duration", value=_format_duration(duration_seconds), inline=False)

        # Add final viewer count if available
        if final_viewer_count is not None:
            embed.add_field(name="Final Viewers", value=f"{final_viewer_count:,}", inline=False)

        # Edit the message
        await message.edit(embed=embed)
        logger.info(f'Guild {guild.name}: Updated announcement for ended stream (message {message_id})')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error editing announcement on stream end: {e}', exc_info=True)


async def _check_stream_status_updates(bot):
    """Check and update viewer counts for streams live >20 minutes."""
    dao = None
    try:
        dao = StreamingAnnouncementDao()

        # Check both platforms
        twitch_announcements = dao.get_announcements_needing_status_update('twitch', update_interval_minutes=20)
        youtube_announcements = dao.get_announcements_needing_status_update('youtube', update_interval_minutes=20)

        all_announcements = twitch_announcements + youtube_announcements

        if not all_announcements:
            return

        logger.debug(f'Checking status for {len(all_announcements)} live streams')

        twitch_service = TwitchService()
        youtube_service = YouTubeService()

        for announcement in all_announcements:
            try:
                guild = bot.get_guild(announcement.guild_id)
                if not guild:
                    continue

                platform = announcement.platform
                streamer_username = announcement.streamer_username
                announcement_id = announcement.id

                # Check if still live and get updated viewer count
                async with aiohttp.ClientSession() as session:
                    current_viewer_count = None

                    if platform == 'twitch':
                        stream_data = await twitch_service.get_stream_info(session, streamer_username)
                        if stream_data.get('data') and len(stream_data['data']) > 0:
                            current_viewer_count = stream_data['data'][0].get('viewer_count')
                    elif platform == 'youtube':
                        channel_id = announcement.streamer_id
                        if channel_id:
                            stream_data = await youtube_service.get_live_stream_info(session, channel_id)
                            if stream_data:
                                current_viewer_count = stream_data.get('viewer_count')

                    if current_viewer_count is not None:
                        # Update the announcement message with new viewer count
                        await _update_announcement_viewer_count(
                            guild,
                            announcement.channel_id,
                            announcement.message_id,
                            current_viewer_count
                        )

                    # Update last status check time
                    dao.update_last_status_check(announcement_id, current_viewer_count)
                    logger.debug(f'Updated viewer count for {platform} {streamer_username} in {guild.name}')

            except Exception as e:
                logger.error(f'Error updating stream status: {e}', exc_info=True)

    except Exception as e:
        logger.error(f'Error in _check_stream_status_updates: {e}', exc_info=True)
    finally:
        if dao:
            try:
                dao.close()
            except Exception as e:
                logger.warning(f'Error closing DAO: {e}')


async def _update_announcement_viewer_count(
    guild,
    channel_id: int,
    message_id: int,
    current_viewer_count: int
):
    """Update viewer count field in announcement embed."""
    try:
        channel = guild.get_channel(channel_id)
        if not channel:
            return

        message = await channel.fetch_message(message_id)
        if not message or not message.embeds:
            return

        embed = message.embeds[0]

        # Find and update "Viewers" field
        for i, field in enumerate(embed.fields):
            if field.name == "Viewers":
                embed.set_field_at(i, name="Viewers", value=f"{current_viewer_count:,}", inline=False)
                await message.edit(embed=embed)
                return

    except Exception as e:
        logger.debug(f'Guild {guild.name}: Could not update viewer count: {e}')


def _format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable format (e.g., '1h 23m 45s')."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def _convert_to_discord_timestamp(timestamp_str):
    """
    Convert ISO 8601 timestamp to Discord timestamp format.

    Discord's timestamp format automatically displays in each user's local timezone.
    """
    try:
        # Try standard format first
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            # Try with fractional seconds
            dt = datetime.strptime(timestamp_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")

        dt_utc = dt.replace(tzinfo=pytz.utc)
        unix_timestamp = int(dt_utc.timestamp())
        return f"<t:{unix_timestamp}:F>"
    except Exception as e:
        logger.error(f'Error converting timestamp {timestamp_str}: {e}', exc_info=True)
        return timestamp_str


def reset_announcement_status(guild_id=None, platform=None, streamer_username=None):
    """Reset announcement status for debugging/testing."""
    global _posted_announcements

    if guild_id is None:
        _posted_announcements.clear()
        logger.info("Reset all announcement statuses")
    elif platform is None:
        _posted_announcements[guild_id] = {'twitch': {}, 'youtube': {}}
        logger.info(f"Reset all announcement statuses for guild {guild_id}")
    elif streamer_username is None:
        if guild_id in _posted_announcements:
            _posted_announcements[guild_id][platform] = {}
            logger.info(f"Reset all {platform} announcement statuses for guild {guild_id}")
    else:
        if guild_id in _posted_announcements and platform in _posted_announcements[guild_id]:
            _posted_announcements[guild_id][platform][streamer_username] = False
            logger.info(f"Reset announcement status for {platform} {streamer_username} in guild {guild_id}")
