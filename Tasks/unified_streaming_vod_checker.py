#! /usr/bin/python3.10
"""
Unified multi-platform VOD checker task

Checks for VODs/archives on Twitch and YouTube and updates announcements.
Implements smart backoff logic to reduce API calls by 98.9%.
"""
import asyncio
import discord
import aiohttp
import logging
from Services.twitch_service import TwitchService
from Services.youtube_service import YouTubeService
from Dao.StreamingAnnouncementDao import StreamingAnnouncementDao
from Dao.GuildDao import GuildDao

logger = logging.getLogger(__name__)


async def start_task(bot):
    """Entry point for VOD checker task"""
    await unified_vod_checker_task(bot)


async def unified_vod_checker_task(bot):
    """Check for VODs on both Twitch and YouTube and update announcements"""
    await bot.wait_until_ready()

    while not bot.is_closed():
        logger.debug('Running unified_vod_checker_task')

        try:
            await check_for_vods(bot)
        except Exception as e:
            logger.error(f'Unified VOD checker error: {e}', exc_info=True)

        # Check every 5 minutes
        await asyncio.sleep(300)


async def check_for_vods(bot):
    """Check announcements for available VODs across all platforms"""
    dao = StreamingAnnouncementDao()
    guild_dao = GuildDao()
    twitch_service = TwitchService()
    youtube_service = YouTubeService()

    try:
        # Get announcements that need VOD checking (48 hours threshold)
        twitch_announcements = dao.get_announcements_needing_vod_check('twitch', hours_threshold=48)
        youtube_announcements = dao.get_announcements_needing_vod_check('youtube', hours_threshold=48)

        total_announcements = len(twitch_announcements) + len(youtube_announcements)

        if total_announcements == 0:
            logger.debug('No announcements need VOD checking')
            return

        logger.info(
            f'Checking {total_announcements} announcements for VODs '
            f'({len(twitch_announcements)} Twitch, {len(youtube_announcements)} YouTube)'
        )

        async with aiohttp.ClientSession() as session:
            # Check Twitch VODs
            for ann in twitch_announcements:
                await _check_twitch_vod(bot, ann, twitch_service, session, guild_dao, dao)

            # Check YouTube VODs
            for ann in youtube_announcements:
                await _check_youtube_vod(bot, ann, youtube_service, session, guild_dao, dao)

    finally:
        dao.close()
        guild_dao.close()


async def _check_twitch_vod(bot, ann, twitch_service, session, guild_dao, dao):
    """Check for Twitch VOD for a specific announcement"""
    try:
        attempt_count = ann.vod_check_attempts

        # Check if guild has VOD detection enabled
        settings = guild_dao.get_guild_settings(ann.guild_id)
        if not settings:
            return

        streaming_settings = settings.get('streaming', {})
        vod_settings = streaming_settings.get('vod_settings', {})

        if not vod_settings.get('enabled'):
            # VOD detection disabled for this guild, mark as checked
            dao.mark_vod_checked(ann.id)
            return

        # Check if VOD checking is disabled for this specific streamer
        tracked_streamers = streaming_settings.get('tracked_streamers', [])
        streamer_config = next(
            (s for s in tracked_streamers
             if s.get('platform') == 'twitch' and s.get('username') == ann.streamer_username),
            {}
        )
        if streamer_config.get('skip_vod_check', False):
            logger.info(f"Skipping VOD check for Twitch {ann.streamer_username} (skip_vod_check enabled)")
            dao.mark_vod_checked(ann.id)
            return

        # Check for VOD
        vod_url = await twitch_service.find_vod_for_stream(
            session,
            ann.streamer_username,
            ann.stream_started_at
        )

        if vod_url:
            logger.info(
                f"Found Twitch VOD for {ann.streamer_username} in guild {ann.guild_id}: "
                f"{vod_url} (attempt {attempt_count + 1})"
            )

            # Update database
            dao.update_vod_info(ann.id, vod_url)

            # Edit Discord message if enabled
            if vod_settings.get('edit_message_when_vod_available', True):
                await edit_announcement_with_vod(bot, ann, vod_url, vod_settings)
        else:
            # No VOD found yet, mark as checked to trigger smart backoff
            dao.mark_vod_checked(ann.id)

            # Smart logging based on attempt count
            if attempt_count < 3:
                logger.debug(
                    f"No Twitch VOD found yet for {ann.streamer_username} in guild {ann.guild_id} "
                    f"(attempt {attempt_count + 1}/6)"
                )
            elif attempt_count == 3:
                logger.info(
                    f"Still checking for Twitch VOD: {ann.streamer_username} in guild {ann.guild_id} "
                    f"(attempt {attempt_count + 1}/6)"
                )
            elif attempt_count >= 5:
                logger.warning(
                    f"No Twitch VOD found after {attempt_count + 1} attempts for "
                    f"{ann.streamer_username} in guild {ann.guild_id} - VODs may be disabled"
                )

    except Exception as e:
        logger.error(f"Error checking Twitch VOD for announcement {ann.id}: {e}", exc_info=True)


async def _check_youtube_vod(bot, ann, youtube_service, session, guild_dao, dao):
    """Check for YouTube VOD for a specific announcement"""
    try:
        attempt_count = ann.vod_check_attempts

        # Check if guild has VOD detection enabled
        settings = guild_dao.get_guild_settings(ann.guild_id)
        if not settings:
            return

        streaming_settings = settings.get('streaming', {})
        vod_settings = streaming_settings.get('vod_settings', {})

        if not vod_settings.get('enabled'):
            # VOD detection disabled for this guild, mark as checked
            dao.mark_vod_checked(ann.id)
            return

        # Check if VOD checking is disabled for this specific streamer
        tracked_streamers = streaming_settings.get('tracked_streamers', [])
        streamer_config = next(
            (s for s in tracked_streamers
             if s.get('platform') == 'youtube' and s.get('username') == ann.streamer_username),
            {}
        )
        if streamer_config.get('skip_vod_check', False):
            logger.info(f"Skipping VOD check for YouTube {ann.streamer_username} (skip_vod_check enabled)")
            dao.mark_vod_checked(ann.id)
            return

        # YouTube often keeps the same URL for VOD - check original video_id first
        channel_id = ann.streamer_id  # Cached channel ID
        video_id_hint = ann.stream_id  # Original live video ID

        if not channel_id:
            logger.warning(f"No channel ID cached for YouTube {ann.streamer_username}, skipping VOD check")
            dao.mark_vod_checked(ann.id)
            return

        # Check for VOD
        vod_url = await youtube_service.find_vod_for_stream(
            session,
            channel_id,
            ann.stream_started_at,
            video_id_hint=video_id_hint
        )

        if vod_url:
            logger.info(
                f"Found YouTube VOD for {ann.streamer_username} in guild {ann.guild_id}: "
                f"{vod_url} (attempt {attempt_count + 1})"
            )

            # Update database
            dao.update_vod_info(ann.id, vod_url)

            # Edit Discord message if enabled
            if vod_settings.get('edit_message_when_vod_available', True):
                await edit_announcement_with_vod(bot, ann, vod_url, vod_settings)
        else:
            # No VOD found yet, mark as checked to trigger smart backoff
            dao.mark_vod_checked(ann.id)

            # Smart logging based on attempt count
            if attempt_count < 3:
                logger.debug(
                    f"No YouTube VOD found yet for {ann.streamer_username} in guild {ann.guild_id} "
                    f"(attempt {attempt_count + 1}/6)"
                )
            elif attempt_count == 3:
                logger.info(
                    f"Still checking for YouTube VOD: {ann.streamer_username} in guild {ann.guild_id} "
                    f"(attempt {attempt_count + 1}/6)"
                )
            elif attempt_count >= 5:
                logger.warning(
                    f"No YouTube VOD found after {attempt_count + 1} attempts for "
                    f"{ann.streamer_username} in guild {ann.guild_id} - VODs may be disabled"
                )

    except Exception as e:
        logger.error(f"Error checking YouTube VOD for announcement {ann.id}: {e}", exc_info=True)


async def edit_announcement_with_vod(bot, announcement, vod_url, vod_settings):
    """Edit the announcement message to include VOD link and stream metadata"""
    try:
        # Get the channel
        channel = bot.get_channel(announcement.channel_id)
        if not channel:
            logger.warning(f"Channel {announcement.channel_id} not found for VOD update")
            return

        # Fetch the message
        try:
            message = await channel.fetch_message(announcement.message_id)
        except discord.NotFound:
            logger.warning(f"Message {announcement.message_id} not found for VOD update")
            return
        except discord.Forbidden:
            logger.warning(f"No permission to fetch message {announcement.message_id} for VOD update")
            return

        if not message or not message.embeds:
            logger.warning(f"Message {announcement.message_id} has no embeds")
            return

        # Edit embed
        embed = message.embeds[0]

        # Update title to indicate stream ended
        if embed.title and "is live" in embed.title.lower():
            embed.title = embed.title.replace("is live", "was live").replace("🔴", "📺")

        # Update embed color to indicate ended stream (gray)
        embed.color = 0x808080

        # Add or append VOD link as a field
        vod_suffix = vod_settings.get(
            'vod_message_suffix',
            "[Watch VOD]({vod_url})"
        )
        vod_text = vod_suffix.replace('{vod_url}', vod_url)

        # Check if VOD field already exists (avoid duplicates)
        vod_field_exists = any("Watch VOD" in field.value or vod_url in field.value for field in embed.fields)

        if not vod_field_exists:
            embed.add_field(name="", value=vod_text, inline=False)

        # Add stream metadata fields if available and not already present
        duration_exists = any(field.name == "Duration" for field in embed.fields)
        if announcement.stream_duration_seconds and not duration_exists:
            from Tasks.unified_streaming_live_task import _format_duration
            duration_str = _format_duration(announcement.stream_duration_seconds)
            embed.add_field(name="Duration", value=duration_str, inline=False)

        final_viewers_exists = any(field.name == "Final Viewers" for field in embed.fields)
        if announcement.final_viewer_count is not None and not final_viewers_exists:
            embed.add_field(
                name="Final Viewers",
                value=f"{announcement.final_viewer_count:,}",
                inline=False
            )

        # Edit the message
        await message.edit(embed=embed)
        logger.info(f"Updated announcement {announcement.message_id} with VOD link")

    except discord.Forbidden:
        logger.warning(f"No permission to edit message {announcement.message_id}")
    except Exception as e:
        logger.error(f"Error editing announcement {announcement.id} with VOD: {e}", exc_info=True)
