#! /usr/bin/python3.10
"""
YouTube VOD checker task

Checks for VODs/archives on YouTube and updates announcements.
For YouTube, VODs are essentially the original video once the livestream ends.
"""
import asyncio
import discord
import aiohttp
import logging
from Services.youtube_service import YouTubeService
from Dao.StreamingAnnouncementDao import StreamingAnnouncementDao
from Dao.GuildDao import GuildDao

logger = logging.getLogger(__name__)


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


async def start_task(bot):
    """Entry point for YouTube VOD checker task."""
    await youtube_vod_checker_task(bot)


async def youtube_vod_checker_task(bot):
    """Check for YouTube VODs and update announcements."""
    await bot.wait_until_ready()

    logger.info("YouTube VOD checker task started (5 minute interval)")

    while not bot.is_closed():
        logger.debug('Running youtube_vod_checker_task')

        try:
            await _check_youtube_vods(bot)
        except Exception as e:
            logger.error(f'YouTube VOD checker error: {e}', exc_info=True)

        await asyncio.sleep(300)  # 5 minutes


async def _check_youtube_vods(bot):
    """Check YouTube announcements for available VODs."""
    dao = StreamingAnnouncementDao()
    guild_dao = GuildDao()
    youtube_service = YouTubeService()

    try:
        # Get YouTube announcements needing VOD check (uses smart backoff)
        announcements = dao.get_announcements_needing_vod_check('youtube')

        if not announcements:
            logger.debug('No YouTube announcements need VOD checking')
            return

        logger.info(f'Checking {len(announcements)} YouTube announcements for VODs')

        async with aiohttp.ClientSession() as session:
            for ann in announcements:
                await _check_single_youtube_vod(bot, ann, youtube_service, session, guild_dao, dao)

    finally:
        dao.close()
        guild_dao.close()


async def _check_single_youtube_vod(bot, ann, youtube_service, session, guild_dao, dao):
    """Check for YouTube VOD for a specific announcement."""
    try:
        attempt_count = ann.vod_check_attempts

        # Check if guild has VOD detection enabled
        settings = guild_dao.get_guild_settings(ann.guild_id)
        if not settings:
            return

        vod_settings = settings.get('youtube', {}).get('vod_settings', {})
        if not vod_settings:
            vod_settings = settings.get('streaming', {}).get('vod_settings', {})

        if not vod_settings.get('enabled') or ann.vod_url is not None:
            return

        # For YouTube, the VOD is the original video once the stream ends
        # Re-fetch video details to ensure it's no longer live
        video_details = await youtube_service.get_video_details(session, ann.stream_id)

        if video_details and not video_details['is_live'] and not video_details['is_upcoming']:
            vod_url = video_details['url']
            logger.info(f"Found YouTube VOD for {ann.streamer_username} (video {ann.stream_id}) in guild {ann.guild_id}: {vod_url}")
            dao.update_vod_info(ann.id, vod_url)

            if vod_settings.get('edit_message_when_vod_available', True):
                await _edit_youtube_announcement_with_vod(bot, ann, vod_url)
        else:
            # Still live, upcoming, or details not found - mark as checked for backoff
            dao.mark_vod_checked(ann.id)

            if attempt_count % 5 == 0 and attempt_count > 0:
                logger.warning(
                    f"Still checking for YouTube VOD: {ann.streamer_username} (video {ann.stream_id}) "
                    f"in guild {ann.guild_id} (attempt {attempt_count + 1})"
                )

    except Exception as e:
        logger.error(f"Error checking YouTube VOD for announcement {ann.id}: {e}", exc_info=True)


async def _edit_youtube_announcement_with_vod(bot, ann, vod_url):
    """Edit the YouTube announcement message to include VOD link."""
    try:
        guild = bot.get_guild(ann.guild_id)
        if not guild:
            logger.warning(f"Guild {ann.guild_id} not found for VOD update")
            return

        channel = guild.get_channel(ann.channel_id)
        if not channel:
            logger.warning(f"Channel {ann.channel_id} not found for VOD update")
            return

        try:
            message = await channel.fetch_message(ann.message_id)
        except (discord.NotFound, discord.Forbidden):
            logger.warning(f"Could not fetch message {ann.message_id} for VOD update")
            return

        if not message or not message.embeds:
            logger.warning(f"Message {ann.message_id} has no embeds")
            return

        embed = message.embeds[0]

        # Update title to indicate stream ended
        if embed.title and "is live" in embed.title.lower():
            embed.title = embed.title.replace("is live", "was live").replace("🔴", "📺")

        # Update color to gray
        embed.color = 0x808080

        # Add VOD link
        vod_text = f"[Watch VOD]({vod_url})"
        vod_field_exists = any("Watch VOD" in field.value for field in embed.fields)

        if not vod_field_exists:
            end_index = next((i for i, field in enumerate(embed.fields) if field.name == "Ended"), len(embed.fields))
            embed.insert_field_at(end_index + 1, name="", value=vod_text, inline=False)

        # Add duration if available
        duration_exists = any(field.name == "Duration" for field in embed.fields)
        if ann.stream_duration_seconds and not duration_exists:
            duration_str = _format_duration(ann.stream_duration_seconds)
            embed.add_field(name="Duration", value=duration_str, inline=False)

        # Add final viewers if available
        final_viewers_exists = any(field.name == "Final Viewers" for field in embed.fields)
        if ann.final_viewer_count is not None and not final_viewers_exists:
            embed.add_field(name="Final Viewers", value=f"{ann.final_viewer_count:,}", inline=False)

        await message.edit(embed=embed)
        logger.info(f"Updated YouTube announcement {ann.message_id} with VOD link")

    except Exception as e:
        logger.error(f"Error editing YouTube announcement with VOD: {e}", exc_info=True)
