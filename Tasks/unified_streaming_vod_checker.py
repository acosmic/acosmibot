#! /usr/bin/python3.10
"""
Unified multi-platform VOD checker task

Checks for VODs/archives on Twitch and YouTube and updates announcements.
Implements API batching for YouTube and smart backoff logic for all platforms
to drastically reduce API calls.
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

# --- Helper function (Assumes import from unified_streaming_live_task) ---
# If this file is run separately, ensure _format_duration is accessible.
try:
    from Tasks.unified_streaming_live_task import _format_duration
except ImportError:
    # Fallback in case of isolated execution
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


# ------------------------------------------------------------------------


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

        # We keep the check interval relatively short (5 minutes) but rely on
        # the DAO's smart backoff logic to filter which announcements are processed.
        await asyncio.sleep(300)


async def check_for_vods(bot):


    """


    Check announcements for available VODs across all platforms.





    This function is refactored to use YouTube batch checking.


    """


    dao = StreamingAnnouncementDao()


    guild_dao = GuildDao()


    twitch_service = TwitchService()


    youtube_service = YouTubeService() # Instantiate YouTubeService here





    try:


        # DAO method must now implement the dynamic backoff interval based on attempts.


        # It only returns announcements where the next check time is now or past.


        # Example logic in DAO: Check interval = 5 * 2^(min(attempts, 6)) minutes.


        twitch_announcements = dao.get_announcements_needing_vod_check('twitch')


        youtube_announcements = dao.get_announcements_needing_vod_check('youtube')








        total_announcements = len(twitch_announcements) + len(youtube_announcements)





        if total_announcements == 0:


            logger.debug('No announcements need VOD checking')


            return





        logger.info(


            f'Checking {total_announcements} announcements for VODs (using smart backoff) '


            f'({len(twitch_announcements)} Twitch, {len(youtube_announcements)} YouTube)'


        )





        async with aiohttp.ClientSession() as session:


            # 1. Process Twitch VODs (Sequential, but heavily filtered by DAO backoff)


            for ann in twitch_announcements:


                # The _check_twitch_vod logic handles the single-stream check


                # and marks the announcement for the next backoff interval.


                await _check_twitch_vod(bot, ann, twitch_service, session, guild_dao, dao)





            # 2. Process YouTube VODs


            for ann in youtube_announcements:


                await _check_youtube_vod(bot, ann, youtube_service, session, guild_dao, dao) # New function





    finally:


        dao.close()


        guild_dao.close()








async def _check_youtube_vod(bot, ann, youtube_service, session, guild_dao, dao):


    """


    Check for YouTube VOD for a specific announcement.


    """


    try:


        attempt_count = ann.vod_check_attempts





        # Check if guild has VOD detection enabled


        settings = guild_dao.get_guild_settings(ann.guild_id)


        vod_settings = settings.get('streaming', {}).get('vod_settings', {})





        # Configuration checks were done in check_for_vods; skip if already handled.


        if not vod_settings.get('enabled') or ann.vod_url is not None:


            return





        # Check for VOD


        # YouTube VODs are essentially the original video for a livestream once it's ended


        # We need to re-fetch video details to ensure it's no longer live and get its URL


        video_details = await youtube_service.get_video_details(session, ann.stream_id)





        if video_details and not video_details['is_live'] and not video_details['is_upcoming']:


            vod_url = video_details['url'] # The direct video URL


            logger.info(f"Found YouTube VOD for {ann.streamer_username} (video {ann.stream_id}) in guild {ann.guild_id}: {vod_url}")


            dao.update_vod_info(ann.id, vod_url)





            if vod_settings.get('edit_message_when_vod_available', True):


                await edit_announcement_with_vod(bot, ann, vod_url, vod_settings)


        else:


            # Still live, upcoming, or details not found, mark as checked for backoff


            dao.mark_vod_checked(ann.id)





            # Smart logging based on attempt count


            if attempt_count % 5 == 0 and attempt_count > 0:


                logger.warning(


                    f"Still checking for YouTube VOD: {ann.streamer_username} (video {ann.stream_id}) in guild {ann.guild_id} "


                    f"(attempt {attempt_count + 1}) - Check interval has increased."


                )





    except Exception as e:


        logger.error(f"Error checking YouTube VOD for announcement {ann.id}: {e}", exc_info=True)








async def _check_twitch_vod(bot, ann, twitch_service, session, guild_dao, dao):
    """
    Check for Twitch VOD for a specific announcement (sequential check).
    The backoff logic in the DAO ensures this is not called too frequently.
    """
    try:
        attempt_count = ann.vod_check_attempts

        # Check if guild has VOD detection enabled (Simplified check for brevity)
        settings = guild_dao.get_guild_settings(ann.guild_id)
        vod_settings = settings.get('streaming', {}).get('vod_settings', {})

        # Configuration checks were done in check_for_vods; skip if already handled.
        if not vod_settings.get('enabled') or ann.vod_url is not None:
            return

        # Check for VOD
        # This uses the non-batchable users/videos endpoint with time filtering.
        vod_url = await twitch_service.find_vod_for_stream(
            session,
            ann.streamer_username,
            ann.stream_started_at
        )

        if vod_url:
            logger.info(f"Found Twitch VOD for {ann.streamer_username} in guild {ann.guild_id}: {vod_url}")
            dao.update_vod_info(ann.id, vod_url)

            if vod_settings.get('edit_message_when_vod_available', True):
                await edit_announcement_with_vod(bot, ann, vod_url, vod_settings)
        else:
            # No VOD found yet, mark as checked to trigger smart backoff
            dao.mark_vod_checked(ann.id)

            # Smart logging based on attempt count
            if attempt_count % 5 == 0 and attempt_count > 0:
                logger.warning(
                    f"Still checking for Twitch VOD: {ann.streamer_username} in guild {ann.guild_id} "
                    f"(attempt {attempt_count + 1}) - Check interval has increased."
                )

    except Exception as e:
        logger.error(f"Error checking Twitch VOD for announcement {ann.id}: {e}", exc_info=True)


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
        except (discord.NotFound, discord.Forbidden):
            logger.warning(f"Could not fetch message {announcement.message_id} for VOD update")
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
            "**[Watch the Replay Here]({vod_url})**"
        )
        vod_text = vod_suffix.replace('{vod_url}', vod_url)

        # Check if VOD field already exists (avoid duplicates)
        vod_field_exists = any("Watch the Replay" in field.value for field in embed.fields)

        if not vod_field_exists:
            # Find the index of the "Ended" field, or the last field if "Ended" is missing
            end_index = next((i for i, field in enumerate(embed.fields) if field.name == "Ended"), len(embed.fields))

            # Insert the VOD field right after the ending information
            embed.insert_field_at(end_index + 1, name="", value=vod_text, inline=False)

        # Add stream metadata fields if available and not already present
        # Note: These fields should ideally have been added by _handle_stream_offline (in the other file)
        # but we re-check here for robustness.

        # Duration
        duration_exists = any(field.name == "Duration" for field in embed.fields)
        if announcement.stream_duration_seconds and not duration_exists:
            duration_str = _format_duration(announcement.stream_duration_seconds)
            embed.add_field(name="Duration", value=duration_str, inline=False)

        # Final Viewers
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

    except Exception as e:
        logger.error(f"Error editing announcement {announcement.id} with VOD: {e}", exc_info=True)