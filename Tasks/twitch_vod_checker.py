#! /usr/bin/python3.10
import asyncio
import discord
import aiohttp
import logging
from Services.twitch_service import TwitchService
from Dao.TwitchAnnouncementDao import TwitchAnnouncementDao
from Dao.GuildDao import GuildDao

logger = logging.getLogger(__name__)


async def start_task(bot):
    """Entry point for VOD checker task"""
    await twitch_vod_checker_task(bot)


async def twitch_vod_checker_task(bot):
    """Check for VODs and update announcements"""
    await bot.wait_until_ready()

    while not bot.is_closed():
        logger.debug('Running twitch_vod_checker_task')

        try:
            await check_for_vods(bot)
        except Exception as e:
            logger.error(f'VOD checker error: {e}', exc_info=True)

        # Check every 5 minutes
        await asyncio.sleep(300)


async def check_for_vods(bot):
    """Check announcements for available VODs"""
    dao = TwitchAnnouncementDao()
    guild_dao = GuildDao()
    tw = TwitchService()

    try:
        # Get announcements that need VOD checking
        announcements = dao.get_announcements_needing_vod_check(hours_threshold=48)

        if not announcements:
            logger.debug('No announcements need VOD checking')
            return

        logger.info(f'Checking {len(announcements)} announcements for VODs')

        async with aiohttp.ClientSession() as session:
            for ann in announcements:
                try:
                    attempt_count = ann.get('vod_check_attempts', 0)

                    # Check if guild has VOD detection enabled
                    settings = guild_dao.get_guild_settings(ann['guild_id'])
                    if not settings:
                        continue

                    vod_settings = settings.get('twitch', {}).get('vod_settings', {})
                    if not vod_settings.get('enabled'):
                        # VOD detection disabled for this guild, mark as checked to avoid re-checking
                        dao.mark_vod_checked(ann['id'])
                        continue

                    # Check if VOD checking is disabled for this specific streamer
                    tracked_streamers = settings.get('twitch', {}).get('tracked_streamers', [])
                    streamer_config = next(
                        (s for s in tracked_streamers if s.get('username') == ann['streamer_username']),
                        {}
                    )
                    if streamer_config.get('skip_vod_check', False):
                        logger.info(f"Skipping VOD check for {ann['streamer_username']} (skip_vod_check enabled)")
                        dao.mark_vod_checked(ann['id'])
                        continue

                    # Check for VOD
                    vod_url = await tw.find_vod_for_stream(
                        session,
                        ann['streamer_username'],
                        ann['stream_started_at']
                    )

                    if vod_url:
                        logger.info(f"Found VOD for {ann['streamer_username']} in guild {ann['guild_id']}: {vod_url} (attempt {attempt_count + 1})")

                        # Update database
                        dao.update_vod_info(ann['id'], vod_url)

                        # Edit Discord message if enabled
                        if vod_settings.get('edit_message_when_vod_available', True):
                            await edit_announcement_with_vod(bot, ann, vod_url, vod_settings)
                    else:
                        # No VOD found yet, mark as checked to avoid immediate re-check
                        dao.mark_vod_checked(ann['id'])

                        # Smart logging based on attempt count
                        if attempt_count < 3:
                            logger.debug(f"No VOD found yet for {ann['streamer_username']} in guild {ann['guild_id']} (attempt {attempt_count + 1}/6)")
                        elif attempt_count == 3:
                            logger.info(f"Still checking for VOD: {ann['streamer_username']} in guild {ann['guild_id']} (attempt {attempt_count + 1}/6)")
                        elif attempt_count >= 5:
                            logger.warning(f"No VOD found after {attempt_count + 1} attempts for {ann['streamer_username']} in guild {ann['guild_id']} - VODs may be disabled for this channel")

                except Exception as e:
                    logger.error(f"Error checking VOD for announcement {ann['id']}: {e}", exc_info=True)
    finally:
        dao.close()
        guild_dao.close()


async def edit_announcement_with_vod(bot, announcement, vod_url, vod_settings):
    """Edit the announcement message to include VOD link and stream metadata"""
    try:
        # Get the channel
        channel = bot.get_channel(announcement['channel_id'])
        if not channel:
            logger.warning(f"Channel {announcement['channel_id']} not found for VOD update")
            return

        # Fetch the message
        try:
            message = await channel.fetch_message(announcement['message_id'])
        except discord.NotFound:
            logger.warning(f"Message {announcement['message_id']} not found for VOD update")
            return
        except discord.Forbidden:
            logger.warning(f"No permission to fetch message {announcement['message_id']} for VOD update")
            return

        if not message or not message.embeds:
            logger.warning(f"Message {announcement['message_id']} has no embeds")
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

        embed.add_field(name="", value=vod_text, inline=False)

        # Add stream metadata fields if available
        if announcement.get('stream_duration_seconds'):
            from Tasks.twitch_live_task import _format_duration
            duration_str = _format_duration(announcement['stream_duration_seconds'])
            embed.add_field(name="Duration", value=duration_str, inline=False)

        if announcement.get('final_viewer_count') is not None:
            embed.add_field(
                name="Final Viewers",
                value=f"{announcement['final_viewer_count']:,}",
                inline=False
            )

        # Edit the message
        await message.edit(embed=embed)
        logger.info(f"Updated announcement {announcement['message_id']} with VOD link")

    except discord.Forbidden:
        logger.warning(f"No permission to edit message {announcement['message_id']}")
    except Exception as e:
        logger.error(f"Error editing announcement {announcement['id']} with VOD: {e}", exc_info=True)
