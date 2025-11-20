#! /usr/bin/python3.10
import discord
from discord.ext import tasks
import asyncio
from datetime import datetime

from Dao.CrossServerPortalDao import CrossServerPortalDao
from logger import AppLogger


logger = AppLogger(__name__).get_logger()


@tasks.loop(seconds=10)
async def check_expired_portals(bot):
    """Check for expired portals and close them"""
    portal_dao = CrossServerPortalDao()
    try:
        expired_portals = portal_dao.get_expired_portals()

        for portal in expired_portals:
            try:
                logger.info(f"Closing expired portal {portal.id} between guilds {portal.guild_id_1} and {portal.guild_id_2}")

                # Close the portal in database
                portal_dao.close_portal(portal.id)

                # Update portal messages to show closed status
                for channel_id, message_id in [
                    (portal.channel_id_1, portal.message_id_1),
                    (portal.channel_id_2, portal.message_id_2)
                ]:
                    try:
                        channel = bot.get_channel(channel_id)
                        if not channel or not message_id:
                            continue

                        message = await channel.fetch_message(message_id)
                        embed = message.embeds[0]

                        # Update embed to show portal is closed
                        embed.title = "🔒 Portal Closed"
                        embed.color = discord.Color.dark_gray()
                        embed.description = (
                            "This portal has closed.\n\n"
                            "**Duration:** 2 minutes (completed)\n\n"
                            "The dimensional gateway has sealed."
                        )

                        await message.edit(embed=embed)

                        # Optionally post a closing message
                        await channel.send(
                            "The portal shimmers and fades away... 🌀✨",
                            delete_after=10
                        )

                    except discord.NotFound:
                        logger.warning(f"Portal message {message_id} not found in channel {channel_id}")
                    except Exception as e:
                        logger.error(f"Error updating closed portal message: {e}")

            except Exception as e:
                logger.error(f"Error closing portal {portal.id}: {e}")

    except Exception as e:
        logger.error(f"Error in check_expired_portals task: {e}")
    finally:
        portal_dao.close()


@check_expired_portals.before_loop
async def before_check_expired_portals():
    """Wait for bot to be ready before starting the task"""
    await asyncio.sleep(5)
    logger.info("Portal manager task starting...")


async def start_task(bot):
    """Start the portal manager background task"""
    check_expired_portals.start(bot)
    logger.info("Portal manager task started")
