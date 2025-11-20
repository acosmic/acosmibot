#! /usr/bin/python3.10
import asyncio
import discord
import logging
import pytz
from datetime import datetime
from Services.twitch_service import TwitchService
from Dao.GuildDao import GuildDao
from Dao.TwitchAnnouncementDao import TwitchAnnouncementDao
import aiohttp

logger = logging.getLogger(__name__)

# Track posted announcements per guild to prevent spam
_posted_announcements = {}
_announcements_lock = asyncio.Lock()


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await twitch_live_check_task(bot)


async def _initialize_announcement_cache(bot):
    """Initialize the announcement cache from database on startup.

    This prevents duplicate announcements after bot restarts by loading
    currently active streams from the database.
    """
    dao = TwitchAnnouncementDao()

    try:
        # Get all announcements where stream hasn't ended yet
        # (stream_ended_at IS NULL means still live)
        active_announcements = dao.execute_query("""
            SELECT DISTINCT guild_id, streamer_username
            FROM TwitchAnnouncements
            WHERE stream_ended_at IS NULL
        """)

        async with _announcements_lock:
            for guild_id, streamer_username in active_announcements:
                if guild_id not in _posted_announcements:
                    _posted_announcements[guild_id] = {}
                _posted_announcements[guild_id][streamer_username] = True

        logger.info(f"Initialized Twitch announcement cache with {len(active_announcements)} active streams")
    except Exception as e:
        logger.error(f"Error initializing Twitch announcement cache: {e}", exc_info=True)
    finally:
        dao.close()


async def twitch_live_check_task(bot):
    """Monitor Twitch streamers and post announcements when they go live."""
    await bot.wait_until_ready()

    # Initialize cache from database on startup to prevent duplicate announcements
    await _initialize_announcement_cache(bot)

    while not bot.is_closed():
        logger.debug('Running twitch_live_check_task')

        try:
            await _check_all_guilds_twitch_streams(bot)

            # Also check for streams that need 20-minute status updates
            await _check_stream_status_updates(bot)
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
    # Get guild settings
    guild_dao = GuildDao()
    try:
        settings = guild_dao.get_guild_settings(guild.id)

        # Check if Twitch notifications are enabled
        if not settings or not settings.get('twitch', {}).get('enabled'):
            return

        # Get announcement channel
        channel_id = settings.get('twitch', {}).get('announcement_channel_id')
        if not channel_id:
            logger.debug(f'Guild {guild.name}: Twitch enabled but no announcement channel configured')
            return

        channel = guild.get_channel(int(channel_id))
        if not channel:
            logger.warning(f'Guild {guild.name}: Twitch announcement channel {channel_id} not found')
            return

        # Get tracked streamers
        tracked_streamers = settings.get('twitch', {}).get('tracked_streamers', [])
        if not tracked_streamers:
            logger.debug(f'Guild {guild.name}: No Twitch streamers configured')
            return

        guild_id = guild.id

        async with _announcements_lock:
            if guild_id not in _posted_announcements:
                _posted_announcements[guild_id] = {}

        # Check each streamer
        tasks = [
            _check_streamer_status(
                streamer_config['twitch_username'],
                streamer_config,
                guild,
                channel,
                tw,
                settings
            )
            for streamer_config in tracked_streamers
            if streamer_config.get('twitch_username')
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        guild_dao.close()


async def _check_streamer_status(streamer_username, streamer_config, guild, channel, tw, settings):
    """Check a specific streamer's status and handle announcements."""
    guild_id = guild.id

    try:
        async with aiohttp.ClientSession() as session:
            is_live = await tw.is_user_live(session, streamer_username)

            async with _announcements_lock:
                already_posted = _posted_announcements[guild_id].get(streamer_username, False)

            if is_live:
                if not already_posted:
                    await _post_live_announcement(
                        streamer_username,
                        streamer_config,
                        guild,
                        channel,
                        tw,
                        session,
                        settings
                    )
                    async with _announcements_lock:
                        _posted_announcements[guild_id][streamer_username] = True
                    logger.info(f'Guild {guild.name}: Posted Twitch announcement for {streamer_username}')
                else:
                    logger.debug(f'Guild {guild.name}: {streamer_username} is live but announcement already posted')
            else:
                if already_posted:
                    # Stream went offline - edit the embed and mark offline
                    dao = TwitchAnnouncementDao()
                    try:
                        # Fetch the announcement from database
                        results = dao.execute_query("""
                            SELECT id, message_id, channel_id, stream_started_at
                            FROM TwitchAnnouncements
                            WHERE guild_id = %s
                            AND streamer_username = %s
                            AND stream_ended_at IS NULL
                            ORDER BY stream_started_at DESC
                            LIMIT 1
                        """, (guild_id, streamer_username))
                        announcement = results[0] if results else None

                        if announcement:
                            announcement_id, message_id, announcement_channel_id, stream_started_at = announcement

                            # Calculate stream duration
                            stream_end_time = datetime.utcnow()
                            duration_seconds = int((stream_end_time - stream_started_at).total_seconds())

                            # Try to get final viewer count from last API call
                            final_viewer_count = None
                            try:
                                async with aiohttp.ClientSession() as session:
                                    stream_data = await tw.get_stream_info(session, streamer_username)
                                    if stream_data.get('data') and len(stream_data['data']) > 0:
                                        final_viewer_count = stream_data['data'][0].get('viewer_count')
                            except Exception as e:
                                logger.debug(f'Guild {guild.name}: Could not fetch final viewer count: {e}')

                            # Edit the announcement message
                            await _edit_announcement_on_stream_end(
                                guild,
                                announcement_channel_id,
                                message_id,
                                stream_started_at,
                                stream_end_time,
                                duration_seconds,
                                final_viewer_count
                            )

                            # Update database with end info
                            dao.mark_stream_offline(guild_id, streamer_username, final_viewer_count, duration_seconds)

                        async with _announcements_lock:
                            _posted_announcements[guild_id][streamer_username] = False
                        logger.debug(f'Guild {guild.name}: {streamer_username} went offline, edited announcement')
                    finally:
                        dao.close()

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error checking {streamer_username}: {e}', exc_info=True)


async def _post_live_announcement(streamer_username, streamer_config, guild, channel, tw, session, settings):
    """Post a live announcement for a streamer."""
    try:
        stream_data = await tw.get_stream_info(session, streamer_username)

        if not stream_data.get('data'):
            logger.warning(f'Guild {guild.name}: No stream data found for {streamer_username}')
            return

        stream_info = stream_data['data'][0]
        profile_picture = await tw.get_user_info(session, streamer_username)
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
        ann_settings = settings.get('twitch', {}).get('announcement_settings', {})
        color_hex = ann_settings.get('color', '0x6441A4')
        color = int(color_hex.replace('0x', ''), 16) if isinstance(color_hex, str) else color_hex

        # Build embed (always use default title)
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
            custom_message = custom_message.replace('{username}', user_name)
            custom_message = custom_message.replace('{game}', game_name)
            custom_message = custom_message.replace('{title}', stream_title)
            custom_message = custom_message.replace('{viewer_count}', str(viewer_count))
            content_parts.append(custom_message)

        # Combine content (pings + custom message) or None
        content = " ".join(content_parts) if content_parts else None

        # Send message
        message = await channel.send(content=content, embed=embed)

        # Store in database for VOD tracking
        dao = TwitchAnnouncementDao()
        try:
            stream_started_dt = datetime.strptime(stream_start_time, "%Y-%m-%dT%H:%M:%SZ")
            dao.create_announcement(
                guild.id,
                streamer_username,
                message.id,
                channel.id,
                stream_started_dt,
                initial_viewer_count=viewer_count,
                stream_title=stream_title,
                game_name=game_name
            )

            logger.info(f'Guild {guild.name}: Posted announcement for {streamer_username} (message {message.id})')
        finally:
            dao.close()

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error posting announcement for {streamer_username}: {e}', exc_info=True)


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
        dao = TwitchAnnouncementDao()
        announcements = dao.get_announcements_needing_status_update()

        if not announcements:
            return

        logger.debug(f'Checking status for {len(announcements)} live streams')

        tw = TwitchService()

        for announcement in announcements:
            try:
                guild = bot.get_guild(announcement['guild_id'])
                if not guild:
                    continue

                streamer_username = announcement['streamer_username']
                announcement_id = announcement['id']

                # Check if still live and get updated viewer count
                async with aiohttp.ClientSession() as session:
                    is_live = await tw.is_user_live(session, streamer_username)

                    if is_live:
                        # Get updated stream info
                        stream_data = await tw.get_stream_info(session, streamer_username)
                        if stream_data.get('data') and len(stream_data['data']) > 0:
                            current_viewer_count = stream_data['data'][0].get('viewer_count')

                            # Try to update the announcement message with new viewer count
                            channel_id = announcement['channel_id']
                            message_id = announcement['message_id']

                            await _update_announcement_viewer_count(
                                guild,
                                channel_id,
                                message_id,
                                current_viewer_count
                            )

                        # Update last status check time
                        dao.update_last_status_check(announcement_id)
                        logger.debug(f'Updated viewer count for {streamer_username} in {guild.name}')

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


def _convert_to_discord_timestamp(stream_start_time):
    """Convert Twitch timestamp to Discord timestamp format.

    Discord's timestamp format automatically displays in each user's local timezone,
    so we just convert to Unix timestamp without any timezone adjustment.
    """
    try:
        dt = datetime.strptime(stream_start_time, "%Y-%m-%dT%H:%M:%SZ")
        dt_utc = dt.replace(tzinfo=pytz.utc)
        unix_timestamp = int(dt_utc.timestamp())
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
