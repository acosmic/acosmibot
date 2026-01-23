#! /usr/bin/python3.10
"""
Twitch VOD checker task

Checks for VODs/archives on Twitch and updates announcements.
Implements smart backoff logic to reduce API calls.
"""
import asyncio
import discord
import aiohttp
import logging
from Services.twitch_service import TwitchService
from Dao.TwitchAnnouncementDao import TwitchAnnouncementDao
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
    """Entry point for Twitch VOD checker task."""
    await twitch_vod_checker_task(bot)


async def twitch_vod_checker_task(bot):
    """Check for Twitch VODs and update announcements."""
    await bot.wait_until_ready()

    logger.info("Twitch VOD checker task started (5 minute interval)")

    while not bot.is_closed():
        logger.debug('Running twitch_vod_checker_task')

        try:
            await _check_twitch_vods(bot)
        except Exception as e:
            logger.error(f'Twitch VOD checker error: {e}', exc_info=True)

        await asyncio.sleep(300)  # 5 minutes


async def _check_twitch_vods(bot):
    """Check Twitch announcements for available VODs."""
    dao = TwitchAnnouncementDao()
    guild_dao = GuildDao()
    twitch_service = TwitchService()

    try:
        # Get announcements needing VOD check (uses smart backoff)
        announcements = dao.get_announcements_needing_vod_check()

        if not announcements:
            logger.debug('No Twitch announcements need VOD checking')
            return

        logger.info(f'Checking {len(announcements)} Twitch announcements for VODs')

        async with aiohttp.ClientSession() as session:
            for ann in announcements:
                await _check_single_twitch_vod(bot, ann, twitch_service, session, guild_dao, dao)

    finally:
        dao.close()
        guild_dao.close()


async def _check_single_twitch_vod(bot, ann, twitch_service, session, guild_dao, dao):
    """Check for Twitch VOD for a specific announcement."""
    try:
        attempt_count = ann.get('vod_check_attempts', 0) if isinstance(ann, dict) else getattr(ann, 'vod_check_attempts', 0)
        ann_id = ann.get('id') if isinstance(ann, dict) else ann.id
        guild_id = ann.get('guild_id') if isinstance(ann, dict) else ann.guild_id
        streamer_username = ann.get('streamer_username') if isinstance(ann, dict) else ann.streamer_username
        stream_started_at = ann.get('stream_started_at') if isinstance(ann, dict) else ann.stream_started_at
        vod_url_existing = ann.get('vod_url') if isinstance(ann, dict) else getattr(ann, 'vod_url', None)
        channel_id = ann.get('channel_id') if isinstance(ann, dict) else ann.channel_id
        message_id = ann.get('message_id') if isinstance(ann, dict) else ann.message_id

        # Check if guild has VOD detection enabled
        settings = guild_dao.get_guild_settings(guild_id)
        if not settings:
            return

        vod_settings = settings.get('twitch', {}).get('vod_settings', {})
        if not vod_settings:
            vod_settings = settings.get('streaming', {}).get('vod_settings', {})

        if not vod_settings.get('enabled') or vod_url_existing is not None:
            return

        # Check for VOD
        vod_url = await twitch_service.find_vod_for_stream(
            session,
            streamer_username,
            stream_started_at
        )

        if vod_url:
            logger.info(f"Found Twitch VOD for {streamer_username} in guild {guild_id}: {vod_url}")
            dao.update_vod_info(ann_id, vod_url)

            if vod_settings.get('edit_message_when_vod_available', True):
                await _edit_twitch_announcement_with_vod(bot, guild_id, channel_id, message_id, vod_url, ann)
        else:
            # No VOD found yet, mark as checked for backoff
            dao.mark_vod_checked(ann_id)

            if attempt_count % 5 == 0 and attempt_count > 0:
                logger.warning(
                    f"Still checking for Twitch VOD: {streamer_username} in guild {guild_id} "
                    f"(attempt {attempt_count + 1})"
                )

    except Exception as e:
        logger.error(f"Error checking Twitch VOD for announcement: {e}", exc_info=True)


async def _edit_twitch_announcement_with_vod(bot, guild_id, channel_id, message_id, vod_url, ann):
    """Edit the Twitch announcement message to include VOD link."""
    try:
        guild = bot.get_guild(guild_id)
        if not guild:
            logger.warning(f"Guild {guild_id} not found for VOD update")
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            logger.warning(f"Channel {channel_id} not found for VOD update")
            return

        try:
            message = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden):
            logger.warning(f"Could not fetch message {message_id} for VOD update")
            return

        if not message or not message.embeds:
            logger.warning(f"Message {message_id} has no embeds")
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
        stream_duration = ann.get('stream_duration_seconds') if isinstance(ann, dict) else getattr(ann, 'stream_duration_seconds', None)
        if stream_duration and not duration_exists:
            duration_str = _format_duration(stream_duration)
            embed.add_field(name="Duration", value=duration_str, inline=False)

        # Add final viewers if available
        final_viewers_exists = any(field.name == "Final Viewers" for field in embed.fields)
        final_viewer_count = ann.get('final_viewer_count') if isinstance(ann, dict) else getattr(ann, 'final_viewer_count', None)
        if final_viewer_count is not None and not final_viewers_exists:
            embed.add_field(name="Final Viewers", value=f"{final_viewer_count:,}", inline=False)

        await message.edit(embed=embed)
        logger.info(f"Updated Twitch announcement {message_id} with VOD link")

    except Exception as e:
        logger.error(f"Error editing Twitch announcement with VOD: {e}", exc_info=True)
