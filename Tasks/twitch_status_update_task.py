#! /usr/bin/python3.10
"""
Twitch status update task

Polls database to update viewer counts and stream metadata for active Twitch streams.
Stream online/offline events are handled by EventSub webhooks via the API.
"""
import asyncio
import discord
import logging
import aiohttp
from Services.twitch_service import TwitchService
from Dao.TwitchAnnouncementDao import TwitchAnnouncementDao

logger = logging.getLogger(__name__)


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await twitch_status_update_task(bot)


async def twitch_status_update_task(bot):
    """Poll DB every 30s to update viewer counts on active Twitch streams."""
    await bot.wait_until_ready()

    logger.info("Twitch status update task started (30s interval)")

    while not bot.is_closed():
        logger.debug('Running twitch_status_update_task')

        try:
            await _check_twitch_status_updates(bot)
        except Exception as e:
            logger.error(f'Twitch status update task error: {e}', exc_info=True)

        await asyncio.sleep(30)


async def _check_twitch_status_updates(bot):
    """
    Check active Twitch streams for viewer count/title updates.
    Query DB for streams needing update, batch check Twitch API, update Discord messages.
    """
    dao = TwitchAnnouncementDao()
    twitch_service = TwitchService()

    try:
        # Fetch Twitch streams needing status update (last_status_check_at > 20 min ago)
        twitch_due = dao.get_announcements_needing_status_update()

        if not twitch_due:
            logger.debug("No Twitch streams needing status update")
            return

        logger.debug(f"Checking status updates for {len(twitch_due)} Twitch streams")

        twitch_usernames = [a['streamer_username'] for a in twitch_due]
        status_update_data = {}

        async with aiohttp.ClientSession() as session:
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
            username = announcement['streamer_username']

            if username in status_update_data:
                data = status_update_data[username]
                stream_info_list = data.get('data', [])

                if stream_info_list:
                    stream_info = stream_info_list[0]
                    new_viewer_count = stream_info.get('viewer_count')
                    new_title = stream_info.get('title')

                    if new_viewer_count is not None:
                        update_tasks.append(_update_twitch_announcement(bot, announcement, new_viewer_count, new_title, dao))
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
        logger.error(f"Error in _check_twitch_status_updates: {e}", exc_info=True)
    finally:
        dao.close()


async def _update_twitch_announcement(bot, announcement: dict, new_viewer_count: int, new_title: str, dao: TwitchAnnouncementDao):
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
            stream_link = f"https://www.twitch.tv/{announcement['streamer_username']}"
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
