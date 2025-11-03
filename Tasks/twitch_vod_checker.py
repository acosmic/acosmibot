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

    # Get announcements that need VOD checking
    announcements = dao.get_announcements_needing_vod_check(hours_threshold=48)

    if not announcements:
        logger.debug('No announcements need VOD checking')
        return

    logger.info(f'Checking {len(announcements)} announcements for VODs')

    async with aiohttp.ClientSession() as session:
        for ann in announcements:
            try:
                # Check if guild has VOD detection enabled
                settings = guild_dao.get_guild_settings(ann['guild_id'])
                if not settings:
                    continue

                vod_settings = settings.get('twitch', {}).get('vod_settings', {})
                if not vod_settings.get('enabled'):
                    # VOD detection disabled for this guild, mark as checked to avoid re-checking
                    dao.mark_vod_checked(ann['id'])
                    continue

                # Check for VOD
                vod_url = await tw.find_vod_for_stream(
                    session,
                    ann['streamer_username'],
                    ann['stream_started_at']
                )

                if vod_url:
                    logger.info(f"Found VOD for {ann['streamer_username']} in guild {ann['guild_id']}: {vod_url}")

                    # Update database
                    dao.update_vod_info(ann['id'], vod_url)

                    # Edit Discord message if enabled
                    if vod_settings.get('edit_message_when_vod_available', True):
                        await edit_announcement_with_vod(bot, ann, vod_url, vod_settings)
                else:
                    # No VOD found yet, mark as checked to avoid immediate re-check
                    dao.mark_vod_checked(ann['id'])
                    logger.debug(f"No VOD found yet for {ann['streamer_username']} in guild {ann['guild_id']}")

            except Exception as e:
                logger.error(f"Error checking VOD for announcement {ann['id']}: {e}", exc_info=True)


async def edit_announcement_with_vod(bot, announcement, vod_url, vod_settings):
    """Edit the announcement message to include VOD link"""
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

        # Get VOD message suffix template
        vod_suffix = vod_settings.get(
            'vod_message_suffix',
            "\n\n📺 **VOD Available:** [Watch Recording]({vod_url})"
        )
        vod_text = vod_suffix.replace('{vod_url}', vod_url)

        # Edit embed
        embed = message.embeds[0]

        # Update title to indicate stream ended
        if embed.title and "is live" in embed.title.lower():
            embed.title = embed.title.replace("is live", "was live").replace("🔴", "📺")

        # Add VOD link to description
        if embed.description:
            # Only add if not already present
            if vod_url not in embed.description:
                embed.description += vod_text
        else:
            embed.description = vod_text

        # Update embed color to indicate ended stream (gray)
        embed.color = 0x808080

        # Edit the message
        await message.edit(embed=embed)
        logger.info(f"Updated announcement {announcement['message_id']} with VOD link")

    except discord.Forbidden:
        logger.warning(f"No permission to edit message {announcement['message_id']}")
    except Exception as e:
        logger.error(f"Error editing announcement {announcement['id']} with VOD: {e}", exc_info=True)
