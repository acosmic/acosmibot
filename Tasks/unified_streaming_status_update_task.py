#! /usr/bin/python3.10
"""
Unified streaming status update task

Polls database every 30s to update viewer counts and stream metadata
for active Twitch streams. Stream.online/offline events are now handled
by EventSub webhooks via the API.

YouTube tracking is currently disabled.
"""
import asyncio
import discord
import logging
import aiohttp
from datetime import datetime
from Services.twitch_service import TwitchService
from Dao.StreamingAnnouncementDao import StreamingAnnouncementDao
from Entities.StreamingAnnouncement import StreamingAnnouncement
from typing import List

logger = logging.getLogger(__name__)


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await unified_streaming_status_update_task(bot)


async def unified_streaming_status_update_task(bot):
    """Poll DB every 30s to update viewer counts on active streams."""
    await bot.wait_until_ready()

    logger.info("Unified streaming status update task started (30s interval)")

    while not bot.is_closed():
        logger.debug('Running unified_streaming_status_update_task')

        try:
            await _check_stream_status_updates(bot)
        except Exception as e:
            logger.error(f'Unified streaming status update task error: {e}', exc_info=True)

        # Check every 30 seconds
        await asyncio.sleep(30)


async def _check_stream_status_updates(bot):
    """
    Check active streams (stream_ended_at IS NULL in DB) for viewer count/title updates.
    Query DB for streams needing update, batch check Twitch API, update Discord messages.
    """
    dao = StreamingAnnouncementDao()
    twitch_service = TwitchService()

    try:
        # Fetch Twitch streams needing status update (last_status_check_at > 20 min ago)
        twitch_due: List[StreamingAnnouncement] = dao.get_announcements_needing_status_update(
            'twitch',
            update_interval_minutes=20
        )

        # NOTE: YouTube tracking is disabled
        # youtube_due = dao.get_announcements_needing_status_update('youtube', update_interval_minutes=20)

        if not twitch_due:
            logger.debug("No Twitch streams needing status update")
            return

        logger.debug(f"Checking status updates for {len(twitch_due)} Twitch streams")

        twitch_usernames = [a.streamer_username for a in twitch_due]

        status_update_data = {}  # {username: stream_data}

        async with aiohttp.ClientSession() as session:
            # Batch check Twitch API
            if twitch_usernames:
                try:
                    twitch_live_data = await twitch_service.get_live_streams_batch(session, twitch_usernames)
                    for username, data in twitch_live_data.items():
                        status_update_data[username] = data
                except Exception as e:
                    logger.error(f"Twitch status update batch failed: {e}")

        # Update announcements
        update_tasks = []
        for announcement in twitch_due:
            username = announcement.streamer_username

            if username in status_update_data:
                data = status_update_data[username]
                stream_info_list = data.get('data', [])

                if stream_info_list:
                    stream_info = stream_info_list[0]
                    new_viewer_count = stream_info.get('viewer_count')

                    if new_viewer_count is not None:
                        update_tasks.append(_update_announcement_viewer_count(bot, announcement, new_viewer_count))
                    else:
                        dao.update_last_status_check(announcement.id)
                else:
                    # No stream data returned - stream may have ended but webhook might have failed
                    logger.warning(f"Stream {username} not live in API check, but announcement still active. Webhook may have failed.")
                    dao.update_last_status_check(announcement.id)
            else:
                # Stream not live anymore - this shouldn't happen if webhooks work correctly
                logger.warning(f"Stream {username} not found in live data, marking check time only")
                dao.update_last_status_check(announcement.id)

        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"Error in _check_stream_status_updates: {e}", exc_info=True)
    finally:
        dao.close()


async def _update_announcement_viewer_count(bot, announcement: StreamingAnnouncement, new_viewer_count: int):
    """Update Discord message with new viewer count"""
    dao = StreamingAnnouncementDao()
    try:
        guild = bot.get_guild(announcement.guild_id)
        if not guild:
            logger.debug(f"Guild {announcement.guild_id} not found for announcement {announcement.id}")
            return

        channel = guild.get_channel(announcement.channel_id)
        if not channel:
            logger.debug(f"Channel {announcement.channel_id} not found for announcement {announcement.id}")
            return

        try:
            message = await channel.fetch_message(announcement.message_id)
        except discord.NotFound:
            logger.warning(f"Message {announcement.message_id} not found during status update (may have been deleted)")
            return
        except discord.Forbidden:
            logger.warning(f"No permission to fetch message {announcement.message_id} in channel {announcement.channel_id}")
            return

        if not message.embeds:
            logger.debug(f"Message {announcement.message_id} has no embeds")
            return

        embed = message.embeds[0]

        # Update the Viewers field in the embed
        updated = False
        for i, field in enumerate(embed.fields):
            if field.name == "Viewers":
                embed.set_field_at(i, name="Viewers", value=f"{new_viewer_count:,}", inline=False)
                updated = True
                break

        if updated:
            await message.edit(embed=embed)
            logger.debug(f"Updated viewer count to {new_viewer_count:,} for stream {announcement.streamer_username}")

        # Update DAO: new viewer count and last status check time
        dao.update_last_status_check(announcement.id, new_viewer_count)

    except discord.HTTPException as e:
        logger.error(f"Discord API error updating announcement viewer count for {announcement.id}: {e}")
    except Exception as e:
        logger.error(f"Error updating announcement viewer count for {announcement.id}: {e}", exc_info=True)
    finally:
        dao.close()
