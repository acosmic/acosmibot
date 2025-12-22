#! /usr/bin/python3.10
"""
Unified multi-platform streaming live task

Monitors Twitch and YouTube streamers using a centralized, batched approach
to drastically reduce API quota usage at scale.
"""
import asyncio
import discord
import logging
import pytz
from datetime import datetime, timedelta
from Services.twitch_service import TwitchService
from Services.youtube_service import YouTubeService
from Dao.GuildDao import GuildDao
from Dao.StreamingAnnouncementDao import StreamingAnnouncementDao
from Entities.StreamingAnnouncement import StreamingAnnouncement
from typing import Dict, List, Set, Tuple, Optional, Any
import aiohttp

logger = logging.getLogger(__name__)

# Track posted announcements per guild to prevent spam
# Structure: {guild_id: {'twitch': {username: bool}, 'youtube': {username: bool}}}
_posted_announcements: Dict[int, Dict[str, Dict[str, bool]]] = {}
_announcements_lock = asyncio.Lock()

# Cache for live stream data retrieved from the central API check
_live_stream_cache: Dict[str, Dict[str, Any]] = {}  # {platform_username: stream_data}




async def start_task(bot):
    """Entry point function that the task manager expects."""
    await unified_streaming_live_check_task(bot)


async def _initialize_announcement_cache(bot):
    """Initialize the announcement cache from database on startup."""
    dao = StreamingAnnouncementDao()
    try:
        # Assumes get_active_announcements_for_cache is a DAO method returning list of entities
        twitch_active: List[StreamingAnnouncement] = dao.get_active_announcements_for_cache('twitch')
    
        async with _announcements_lock:
            for announcement in twitch_active:
                guild_id = announcement.guild_id
                username = announcement.streamer_username
                _posted_announcements.setdefault(guild_id, {'twitch': {}, 'youtube': {}}).setdefault('twitch', {})[
                    username] = True
    
        total_active = len(twitch_active)
        logger.info(
            f"Initialized streaming announcement cache with {total_active} active streams "
            f"({len(twitch_active)} Twitch)"
        )
    except Exception as e:
        logger.error(f"Error initializing streaming announcement cache: {e}", exc_info=True)
    finally:
        dao.close()


async def unified_streaming_live_check_task(bot):
    """Monitor Twitch and YouTube streamers using a centralized, batched approach."""
    await bot.wait_until_ready()
    await _initialize_announcement_cache(bot)

    while not bot.is_closed():
        logger.debug('Running unified_streaming_live_check_task')

        try:
            # 1. Centralized API check (makes few API calls)
            await _check_all_unique_streams_batched(bot)

            # 2. Process announcements for all guilds (uses the cache, makes no API calls)
            await _process_announcements_for_all_guilds(bot)

            # 3. Check for streams that need 20-minute status updates (still necessary)
            await _check_stream_status_updates(bot)

        except Exception as e:
            logger.error(f'Unified streaming live check task error: {e}', exc_info=True)

        await asyncio.sleep(60)


async def _get_unique_streamers_to_check(bot) -> Dict[str, Set[str]]:
    """Aggregate all unique streamers across all guilds."""
    unique_streamers = {'twitch': set()}
    guild_dao = GuildDao()

    try:
        for guild in bot.guilds:
            # FIX: Check if settings is None before using it
            settings = guild_dao.get_guild_settings(guild.id)
            if settings is None:
                logger.debug(f"Skipping guild {guild.name}: No settings found in DAO.")
                continue  # Skip to the next guild

            streaming_settings = settings.get('streaming', {})

            if streaming_settings.get('enabled') and streaming_settings.get('announcement_channel_id'):
                for streamer_config in streaming_settings.get('tracked_streamers', []):
                    platform = streamer_config.get('platform')
                    username = streamer_config.get('username')

                    if platform in unique_streamers and username:
                        unique_streamers[platform].add(username)
    finally:
        guild_dao.close()
        return unique_streamers


async def _check_all_unique_streams_batched(bot):
    """
    Performs batch API checks for all unique streamers collected from all guilds.
    Updates the global _live_stream_cache. Implements YouTube quota backoff.
    """
    global _live_stream_cache, _youtube_quota_exceeded, _youtube_quota_reset_time
    _live_stream_cache = {}  # Clear cache for the new cycle

    unique_streamers = await _get_unique_streamers_to_check(bot)
    twitch_service = TwitchService()
    youtube_service = YouTubeService()
    dao = StreamingAnnouncementDao()

    # --- Start main logic block ---
    try:
        # Handle YouTube Quota Backoff
        if _youtube_quota_exceeded:
            if _youtube_quota_reset_time and datetime.now() >= _youtube_quota_reset_time:
                logger.warning("YouTube Quota soft-reset time reached. Attempting checks again.")
                _youtube_quota_exceeded = False
                _youtube_quota_reset_time = None
            else:
                logger.debug(f"Skipping YouTube checks: Quota exceeded. Resume at {_youtube_quota_reset_time}")

        async with aiohttp.ClientSession() as session:
            # 1. Twitch Batch Check
            twitch_users = list(unique_streamers['twitch'])
            if twitch_users:
                try:
                    twitch_live_data = await twitch_service.get_live_streams_batch(session, twitch_users)
                    for username, data in twitch_live_data.items():
                        _live_stream_cache[f'twitch_{username}'] = data
                    logger.info(f"Twitch batch check found {len(twitch_live_data)} streams live.")
                except Exception as e:
                    logger.error(f"Twitch batch check failed: {e}", exc_info=True)

            # 2. YouTube Check: Now handled by webhooks, no longer polled here.
            # The process_youtube_events_task will handle creating/updating StreamingAnnouncements
            # based on incoming WebSub notifications.
            # _youtube_quota_exceeded and _youtube_quota_reset_time are no longer managed here.

    # --- Ensure DAO closes correctly ---
    finally:
        dao.close()




async def _process_announcements_for_all_guilds(bot):
    """
    Iterates through all guilds and checks their streamers against the global
    _live_stream_cache to trigger announcements or offline handling.
    """
    guild_dao = GuildDao()
    twitch_service = TwitchService()

    try:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for guild in bot.guilds:
                settings = guild_dao.get_guild_settings(guild.id)


                if settings is None:
                    logger.debug(f"Skipping guild {guild.name}: No settings found in DAO for announcement processing.")
                    continue


                streaming_settings = settings.get('streaming', {})

                if not streaming_settings.get('enabled'):
                    continue

                channel_id = streaming_settings.get('announcement_channel_id')
                channel = guild.get_channel(int(channel_id)) if channel_id else None

                if not channel:
                    continue

                tracked_streamers = streaming_settings.get('tracked_streamers', [])

                for streamer_config in tracked_streamers:
                    platform = streamer_config.get('platform')
                    username = streamer_config.get('username')
                    cache_key = f'{platform}_{username}'

                    is_live_in_cache = cache_key in _live_stream_cache
                    stream_data = _live_stream_cache.get(cache_key)

                    async with _announcements_lock:
                        already_posted = _posted_announcements.get(guild.id, {}).get(platform, {}).get(username, False)

                    if is_live_in_cache:
                        if not already_posted:
                            # New Stream detected -> Post announcement
                            if platform == 'twitch':
                                tasks.append(_post_twitch_live_announcement_from_cache(
                                    username, streamer_config, stream_data, guild, channel, twitch_service, session,
                                    streaming_settings
                                ))
                            elif platform == 'youtube':
                                # YouTube announcements are now handled by the webhook processing task
                                # This block should only handle Twitch.
                                logger.debug(f"Skipping YouTube announcement for {username} in guild {guild.id}. Handled by webhooks.")

                            async with _announcements_lock:
                                _posted_announcements.setdefault(guild.id, {}).setdefault(platform, {})[username] = True

                    elif already_posted:
                        # Stream is NOT live in the cache, but was posted -> Handle Offline
                        dao = StreamingAnnouncementDao()
                        tasks.append(_handle_stream_offline_from_cache(
                            guild, guild.id, username, platform, dao, twitch_service, youtube_service, session
                        ))
                        async with _announcements_lock:
                            _posted_announcements.setdefault(guild.id, {}).setdefault(platform, {})[username] = False

            await asyncio.gather(*tasks, return_exceptions=True)

    finally:
        guild_dao.close()


# --- MIGRATED/FIXED POSTING/HANDLING FUNCTIONS ---

async def _post_twitch_live_announcement_from_cache(username, streamer_config, stream_data, guild, channel, tw, session,
                                                    settings):
    """Post a live announcement for a Twitch streamer using cached data (MIGRATED)."""
    try:
        stream_info = stream_data['data'][0]

        # Get profile picture (needs a separate API call, but only once)
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

        # Build content with pings and custom message (using the helper)
        content = _build_announcement_content_twitch(streamer_config, user_name, game_name, stream_title, viewer_count)

        # Send message
        message = await channel.send(content=content, embed=embed)

        # Store in database
        dao = StreamingAnnouncementDao()
        try:
            stream_started_dt = datetime.strptime(stream_start_time, "%Y-%m-%dT%H:%M:%SZ")
            dao.create_announcement(
                platform='twitch',
                guild_id=guild.id,
                channel_id=channel.id,
                message_id=message.id,
                streamer_username=username,
                streamer_id=stream_info.get('user_id'),
                stream_id=stream_info.get('id'),
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





async def _handle_stream_offline_from_cache(guild, guild_id, username, platform, dao, tw, yt, session):
    """Handle stream going offline - fetch current announcement from DB and proceed."""
    try:
        local_dao = StreamingAnnouncementDao()
        announcement = local_dao.get_active_stream_for_streamer(platform, guild_id, username)

        if not announcement:
            logger.warning(f'Guild {guild.name}: No active announcement found for {platform} {username}')
            return

        stream_end_time = datetime.utcnow().replace(tzinfo=pytz.utc)
        duration_seconds = int(
            (stream_end_time - announcement.stream_started_at.replace(tzinfo=pytz.utc)).total_seconds())

        final_viewer_count = announcement.initial_viewer_count  # Default to last known count

        # Edit the announcement message (using the dedicated helper)
        await _edit_announcement_on_stream_end(
            guild,
            announcement.channel_id,
            announcement.message_id,
            announcement.stream_started_at,
            stream_end_time,
            duration_seconds,
            final_viewer_count
        )

        # Update database with end info and initialize VOD backoff
        local_dao.mark_stream_offline(
            platform,
            guild_id,
            username,
            stream_end_time.replace(tzinfo=None),  # Store naive datetime
            final_viewer_count
        )
        logger.debug(f'Guild {guild.name}: {username} went offline, edited announcement')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error handling offline stream: {e}', exc_info=True)
    finally:
        local_dao.close()


# --- MIGRATED/SHARED HELPER FUNCTIONS ---

def _build_announcement_content_twitch(streamer_config, user_name, game_name, stream_title, viewer_count):
    """Builds the raw message content, handling pings and custom messages (MIGRATED)."""
    mention_parts = []

    # Check for the unified 'mention' field (simple: everyone/here/role ID)
    mention = streamer_config.get('mention', '').lower()
    if mention == 'everyone':
        mention_parts.append("@everyone")
    elif mention == 'here':
        mention_parts.append("@here")
    elif mention.startswith('<@&'):
        mention_parts.append(mention)
    # Support for the old role list field, if still used
    if streamer_config.get('mention_role_ids'):
        role_ids = streamer_config['mention_role_ids']
        if isinstance(role_ids, list):
            for role_id in role_ids:
                mention_parts.append(f"<@&{role_id}>")

    content_parts = []

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

    return " ".join(content_parts) if content_parts else None


async def _edit_announcement_on_stream_end(
        guild,
        channel_id: int,
        message_id: int,
        stream_started_at: datetime,
        stream_end_time: datetime,
        duration_seconds: int,
        final_viewer_count: int = None
):
    """Edit announcement embed when stream ends with timing and viewer info (MIGRATED)."""
    try:
        channel = guild.get_channel(channel_id)
        if not channel:
            return

        message = await channel.fetch_message(message_id)
        if not message or not message.embeds:
            return

        embed = message.embeds[0]

        # Preserve fields we want to keep (everything except "Viewers")
        fields_to_keep = []
        for field in embed.fields:
            if field.name != "Viewers":
                fields_to_keep.append((field.name, field.value, field.inline))

        # Update title: Change live status and icon
        if "🔴" in embed.title:
            embed.title = embed.title.replace("🔴 ", "⚫ ").replace("is live", "was live")

        # Remove image preview
        embed.set_image(url=None)

        # Update color to gray for ended stream
        embed.color = 0x808080

        # Convert timestamps to Discord format
        started_ts = int(stream_started_at.replace(tzinfo=pytz.utc).timestamp())
        ended_ts = int(stream_end_time.replace(tzinfo=pytz.utc).timestamp())

        # *** FIX START: Clear old fields and add the ones we kept ***
        embed.clear_fields()

        for name, value, inline in fields_to_keep:
            embed.add_field(name=name, value=value, inline=inline)

        # Add stream end metadata fields
        embed.add_field(name="Ended", value=f"<t:{ended_ts}:F>", inline=False)
        embed.add_field(name="Duration", value=_format_duration(duration_seconds), inline=False)

        # Add final viewer count
        if final_viewer_count is not None:
            embed.add_field(name="Final Viewers", value=f"{final_viewer_count:,}", inline=False)

        await message.edit(embed=embed)
        logger.debug(f'Guild {guild.name}: Successfully edited announcement for message {message_id}')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error editing announcement on stream end: {e}', exc_info=True)


async def _update_announcement_viewer_count(bot, announcement: StreamingAnnouncement, new_viewer_count: int):
    """Edits the Discord message and updates the DAO with the new viewer count."""
    dao = StreamingAnnouncementDao()
    try:
        guild = bot.get_guild(announcement.guild_id)
        if not guild: return

        channel = guild.get_channel(announcement.channel_id)
        if not channel: return

        message = await channel.fetch_message(announcement.message_id)
        if not message.embeds: return

        embed = message.embeds[0]

        # Update the Viewers field in the embed (MIGRATED LOGIC)
        for i, field in enumerate(embed.fields):
            if field.name == "Viewers":
                embed.set_field_at(i, name="Viewers", value=f"{new_viewer_count:,}", inline=False)
                break

        await message.edit(embed=embed)

        # Update DAO: new viewer count and last status check time
        dao.update_last_status_check(announcement.id, new_viewer_count)

    except discord.NotFound:
        logger.warning(f"Message {announcement.message_id} not found during status update.")
    except Exception as e:
        logger.error(f"Error updating announcement viewer count for {announcement.id}: {e}", exc_info=True)
    finally:
        dao.close()


def _format_duration(seconds: int) -> str:
    """Helper to format duration in seconds to human-readable format (e.g., '1h 23m 45s')."""
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


def _convert_to_discord_timestamp(dt_input: Any) -> str:
    """Convert timestamp to Discord Unix Timestamp format."""
    try:
        if isinstance(dt_input, str):
            # Handle ISO 8601 string input
            try:
                dt_obj = datetime.fromisoformat(dt_input.replace('Z', '+00:00'))
            except ValueError:
                dt_obj = datetime.strptime(dt_input.split('.')[0], "%Y-%m-%dT%H:%M:%S")
        elif isinstance(dt_input, datetime):
            dt_obj = dt_input
        else:
            return str(dt_input)

        dt_utc = dt_obj.replace(tzinfo=pytz.utc)
        unix_timestamp = int(dt_utc.timestamp())
        return f"<t:{unix_timestamp}:R>"
    except Exception:
        return str(dt_input)


# --- Status Update (Optimized) ---

async def _check_stream_status_updates(bot):
    """
    Checks for active streams that are due for a viewer count update based on the DAO.
    """
    dao = StreamingAnnouncementDao()
    twitch_service = TwitchService()

    try:
        # 1. Fetch ALL streams needing an update (DAO uses time-based filtering)
        twitch_due = dao.get_announcements_needing_status_update('twitch', update_interval_minutes=20)


        status_update_data = {}  # {platform_username: stream_data}

        async with aiohttp.ClientSession() as session:
            # a. Twitch Batch Check
            if twitch_usernames:
                try:
                    twitch_live_data = await twitch_service.get_live_streams_batch(session, twitch_usernames)
                    for username, data in twitch_live_data.items():
                        status_update_data[f'twitch_{username}'] = data
                except Exception as e:
                    logger.error(f"Twitch status update batch failed: {e}")



        # 3. Process Updates
        all_due_announcements = twitch_due
        update_tasks = []
        for announcement in all_due_announcements:
            cache_key = f'{announcement.platform}_{announcement.streamer_username}'

            if cache_key in status_update_data:
                data = status_update_data[cache_key]

                if announcement.platform == 'twitch':
                    new_viewer_count = data.get('data', [{}])[0].get('viewer_count')
                else:
                    new_viewer_count = data.get('viewer_count')

                if new_viewer_count is not None and new_viewer_count != announcement.initial_viewer_count:
                    update_tasks.append(_update_announcement_viewer_count(bot, announcement, new_viewer_count))
                else:
                    dao.update_last_status_check(announcement.id)
            else:
                dao.update_last_status_check(announcement.id)

        await asyncio.gather(*update_tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"Error in _check_stream_status_updates: {e}", exc_info=True)
    finally:
        dao.close()


async def reset_announcement_status():
    """Function to clear the in-memory cache, usually called on specific events/commands."""
    global _posted_announcements
    async with _announcements_lock:
        _posted_announcements = {}
    logger.warning("In-memory streaming announcement cache has been reset.")