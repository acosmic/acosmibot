#! /usr/bin/python3.10
"""
Kick status update task

Polls database to update viewer counts and stream metadata for active Kick streams.
Stream online/offline events are handled by webhooks via the API.
"""
import asyncio
import discord
import logging
import aiohttp
from Services.kick_service import KickService
from Dao.KickAnnouncementDao import KickAnnouncementDao

logger = logging.getLogger(__name__)


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await kick_status_update_task(bot)


async def kick_status_update_task(bot):
    """Poll DB every 30s to update viewer counts on active Kick streams."""
    await bot.wait_until_ready()

    logger.info("Kick status update task started (30s interval)")

    while not bot.is_closed():
        logger.debug('Running kick_status_update_task')

        try:
            await _check_kick_status_updates(bot)
        except Exception as e:
            logger.error(f'Kick status update task error: {e}', exc_info=True)

        await asyncio.sleep(30)


async def _check_kick_status_updates(bot):
    """
    Check active Kick streams for viewer count/title updates.
    Query DB for streams needing update, batch check Kick API, update Discord messages.
    """
    dao = KickAnnouncementDao()
    kick_service = KickService()

    try:
        # Fetch Kick streams needing status update (last_status_check_at > 20 min ago)
        kick_due = dao.get_announcements_needing_status_update()

        if not kick_due:
            logger.debug("No Kick streams needing status update")
            return

        logger.debug(f"Checking status updates for {len(kick_due)} Kick streams")

        kick_usernames = [a['streamer_username'] for a in kick_due]
        status_update_data = {}

        # Simple session - Kick's official public API handles auth via OAuth token
        async with aiohttp.ClientSession() as session:
            if kick_usernames:
                try:
                    kick_live_data = await kick_service.get_live_streams_batch(session, kick_usernames)
                    for username, data in kick_live_data.items():
                        status_update_data[username] = data
                except Exception as e:
                    logger.error(f"Kick status update batch failed: {e}")

        # Update announcements
        update_tasks = []
        for announcement in kick_due:
            username = announcement['streamer_username']

            if username in status_update_data:
                data = status_update_data[username]
                stream_info = data.get('livestream')

                if stream_info and stream_info.get('is_live'):
                    new_viewer_count = stream_info.get('viewer_count')
                    new_title = stream_info.get('session_title')

                    if new_viewer_count is not None:
                        update_tasks.append(_update_kick_announcement(bot, announcement, new_viewer_count, new_title, dao))
                    else:
                        dao.update_last_status_check(announcement['id'])
                else:
                    logger.warning(f"Stream {username} not live in API check, but announcement still active.")
                    dao.update_last_status_check(announcement['id'])
            else:
                logger.warning(f"Stream {username} not found in live data, marking check time only")
                dao.update_last_status_check(announcement['id'])

        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"Error in _check_kick_status_updates: {e}", exc_info=True)
    finally:
        dao.close()


async def _update_kick_announcement(bot, announcement: dict, new_viewer_count: int, new_title: str, dao: KickAnnouncementDao):
    """Update Discord message with new viewer count and title."""
    try:
        guild = bot.get_guild(announcement['guild_id'])
        if not guild:
            logger.debug(f"Guild {announcement['guild_id']} not found")
            return

        channel = guild.get_channel(announcement['channel_id'])
        if not channel:
            logger.debug(f"Channel {announcement['channel_id']} not found")
            return

        try:
            message = await channel.fetch_message(announcement['message_id'])
        except discord.NotFound:
            logger.warning(f"Message {announcement['message_id']} not found (may have been deleted)")
            return
        except discord.Forbidden:
            logger.warning(f"No permission to fetch message {announcement['message_id']}")
            return

        if not message.embeds:
            logger.debug(f"Message {announcement['message_id']} has no embeds")
            return

        embed = message.embeds[0]

        # Update the description (stream title) if provided
        if new_title:
            stream_link = f"https://kick.com/{announcement['streamer_username']}"
            embed.description = f"### [{new_title}]({stream_link})"

        # Update the Viewers field
        updated = False
        for i, field in enumerate(embed.fields):
            if field.name == "Viewers":
                embed.set_field_at(i, name="Viewers", value=f"{new_viewer_count:,}", inline=False)
                updated = True
                break

        if updated or new_title:
            await message.edit(embed=embed)
            log_parts = []
            if updated:
                log_parts.append(f"viewer count to {new_viewer_count:,}")
            if new_title:
                log_parts.append(f"title to '{new_title}'")
            logger.debug(f"Updated {' and '.join(log_parts)} for stream {announcement['streamer_username']}")

        # Update DAO
        dao.update_last_status_check(announcement['id'], new_viewer_count)

    except discord.HTTPException as e:
        logger.error(f"Discord API error updating announcement {announcement['id']}: {e}")
    except Exception as e:
        logger.error(f"Error updating announcement {announcement['id']}: {e}", exc_info=True)
