import asyncio
import discord
import logging

logger = logging.getLogger(__name__)


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await streaming_monitor_task(bot)


async def streaming_monitor_task(bot):
    """Monitor streaming members and manage Live Now role every minute."""
    await bot.wait_until_ready()


    while not bot.is_closed():
        logger.debug(f'Running streaming_monitor_task')

        try:
            await _check_all_guilds_streaming_status(bot)
        except Exception as e:
            logger.error(f'Streaming monitor task error: {e}')

        await asyncio.sleep(60)


async def _check_all_guilds_streaming_status(bot):
    """Check streaming status for all guilds."""
    for guild in bot.guilds:
        try:
            await _check_guild_streaming_status(guild)
        except Exception as e:
            logger.error(f'Error checking streaming status for guild {guild.name}: {e}')


async def _check_guild_streaming_status(guild):
    """Check streaming status for a specific guild."""
    # Get roles for this guild - check for both "Live Now" and "Streamers"
    live_now_role = discord.utils.get(guild.roles, name="Live Now")

    # Check for "Streamer" or "Streamers" role (some servers use plural)
    streamer_role = discord.utils.get(guild.roles, name="Streamer")
    if not streamer_role:
        streamer_role = discord.utils.get(guild.roles, name="Streamers")

    if not live_now_role:
        logger.warning(f'Guild {guild.name}: "Live Now" role not found')
        return

    if not streamer_role:
        logger.warning(f'Guild {guild.name}: "Streamer" or "Streamers" role not found')
        return

    members_processed = 0
    roles_added = 0
    roles_removed = 0

    # Check all members with the Streamer/Streamers role
    for member in guild.members:
        if streamer_role not in member.roles:
            continue

        members_processed += 1

        try:
            # Check if member is currently streaming
            is_streaming = _is_member_streaming(member)

            if is_streaming:
                if live_now_role not in member.roles:
                    await member.add_roles(live_now_role, reason="Started streaming")
                    roles_added += 1
                    logger.info(f'Guild {guild.name}: Added "Live Now" role to {member.display_name}')
                else:
                    logger.debug(f'Guild {guild.name}: {member.display_name} is streaming and already has the role')
            else:
                if live_now_role in member.roles:
                    await member.remove_roles(live_now_role, reason="Stopped streaming")
                    roles_removed += 1
                    logger.info(f'Guild {guild.name}: Removed "Live Now" role from {member.display_name}')

        except discord.HTTPException as e:
            logger.error(f'Guild {guild.name}: Failed to update roles for {member.display_name}: {e}')
        except Exception as e:
            logger.error(f'Guild {guild.name}: Unexpected error processing {member.display_name}: {e}')

    if members_processed > 0:
        logger.debug(f'Guild {guild.name}: Processed {members_processed} streamers, '
                     f'added {roles_added} roles, removed {roles_removed} roles')


def _is_member_streaming(member):
    """Check if a member is currently streaming on any platform."""
    streaming_activities = [
        activity for activity in member.activities
        if isinstance(activity, discord.Streaming)
    ]
    return len(streaming_activities) > 0


# Optional: More detailed streaming info
async def _get_streaming_details(member):
    """Get detailed streaming information for a member."""
    streaming_activities = [
        activity for activity in member.activities
        if isinstance(activity, discord.Streaming)
    ]

    if not streaming_activities:
        return None

    # Return details about the first streaming activity
    activity = streaming_activities[0]
    return {
        'platform': activity.platform,
        'name': activity.name,
        'details': activity.details,
        'url': activity.url,
        'game': activity.game if hasattr(activity, 'game') else None
    }


# import discord
# import logging
# logger = logging.getLogger(__name__)
#
# async def start_task(bot):
#     """Entry point function that the task manager expects."""
#     await check_streaming_members_task(bot)
#
# async def check_streaming_members_task(bot):
#     live_now_role_name = "Live Now"
#     streamer_role_name = "Streamer"
#     live_now_role = discord.utils.get(bot.guilds[0].roles, name=live_now_role_name)
#     streamer_role = discord.utils.get(bot.guilds[0].roles, name=streamer_role_name)
#     for guild in bot.guilds:
#         for member in guild.members:
#             if streamer_role in member.roles:
#                 streaming_activities = [activity for activity in member.activities if
#                                         isinstance(activity, discord.Streaming)]
#
#                 if streaming_activities:
#                     if live_now_role not in member.roles:
#                         logger.info(f'{member.display_name} is streaming')
#                         await member.add_roles(live_now_role)
#                     else:
#                         logger.info(f'{member.display_name} is streaming and already has the role')
#                 else:
#                     if live_now_role in member.roles:
#                         logger.info(f'{member.display_name} is not streaming')
#                         await member.remove_roles(live_now_role)