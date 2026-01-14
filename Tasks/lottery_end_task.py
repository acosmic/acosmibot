import asyncio
import random
from datetime import datetime, timedelta, timezone
import logging
import discord

from Dao.GuildDao import GuildDao
from Dao.GuildUserDao import GuildUserDao
from Dao.LotteryEventDao import LotteryEventDao
from Dao.LotteryParticipantDao import LotteryParticipantDao

logger = logging.getLogger(__name__)

async def start_task(bot):
    """Entry point function that the task manager expects."""
    await lottery_end_task(bot)

async def lottery_end_task(bot):
    """Multi-guild lottery end task that monitors and ends lottery events."""
    await bot.wait_until_ready()

    while not bot.is_closed():
        logger.info('Running lottery_end_task')

        try:
            await _process_all_guild_lotteries(bot)
        except Exception as e:
            logger.error(f'Lottery end task error: {e}')

        await asyncio.sleep(60)


async def _process_all_guild_lotteries(bot):
    """Process lottery events for all guilds."""
    le_dao = LotteryEventDao()
    try:
        # Get all current lottery events across all guilds
        current_lotteries = le_dao.get_all_current_events()

        if not current_lotteries:
            logger.info('No active lottery events found')
            return

        for lottery_event in current_lotteries:
            try:
                guild = bot.get_guild(lottery_event.guild_id)
                if not guild:
                    logger.warning(f'Guild {lottery_event.guild_id} not found, skipping lottery {lottery_event.id}')
                    continue

                # Now we can simply get the channel by ID
                channel = guild.get_channel(lottery_event.channel_id)
                if not channel:
                    logger.warning(f'Channel {lottery_event.channel_id} not found in guild {guild.name}, skipping lottery')
                    continue

                await _process_lottery_event(lottery_event, guild, channel)

            except Exception as e:
                logger.error(f'Error processing lottery {lottery_event.id} in guild {lottery_event.guild_id}: {e}')
    finally:
        le_dao.close()


async def _process_lottery_event(lottery_event, guild, channel):
    """Process a single lottery event."""
    remaining_time = lottery_event.end_time - datetime.utcnow()
    logger.debug(f'Guild {guild.name}: Lottery {lottery_event.id} - Remaining time: {remaining_time}')

    if remaining_time <= timedelta(minutes=1):
        await _end_lottery(lottery_event, guild, channel)
    elif remaining_time <= timedelta(minutes=30):
        await _send_lottery_reminder(lottery_event, guild, channel, remaining_time)


async def _end_lottery(lottery_event, guild, channel):
    """End a lottery event and select a winner."""
    logger.info(f'Guild {guild.name}: Ending lottery event {lottery_event.id}')

    # Get all required DAOs
    le_dao = LotteryEventDao()
    guild_dao = GuildDao()  # Use GuildDao instead of VaultDao
    guild_user_dao = GuildUserDao()  # Need this for winner's currency
    lp_dao = LotteryParticipantDao()
    try:
        # Get lottery credits from guild vault
        lottery_credits = guild_dao.get_vault_currency(guild.id)

        # Get participants using lottery_event.id (not message_id)
        participants = lp_dao.get_participants(lottery_event.id)

        if not participants:
            logger.warning(f'Guild {guild.name}: No participants in lottery {lottery_event.id}')
            await _cleanup_empty_lottery(lottery_event, guild, channel, le_dao)
            return

        # Select winner
        winner = random.choice(participants)
        discord_winner = guild.get_member(winner.participant_id)

        if not discord_winner:
            logger.warning(f'Guild {guild.name}: Winner {winner.participant_id} not found in guild')
            # Could implement fallback logic here
            return

        # Get winner's guild user record (currency is guild-specific)
        winner_guild_user = guild_user_dao.get_or_create_guild_user_from_discord(discord_winner, guild.id)

        if not winner_guild_user:
            logger.error(f'Guild {guild.name}: Failed to get guild user for winner {discord_winner.name}')
            return

        # Send winner announcement
        lottery_role = discord.utils.get(guild.roles, name="LotteryParticipant")
        role_mention = lottery_role.mention if lottery_role else "@LotteryParticipant"

        await channel.send(
            f'# {role_mention} Congratulations to {discord_winner.mention} '
            f'for winning {lottery_credits:,.0f} Credits in the lottery! '
            f'🎰✨'
        )

        # Update database records
        await _update_lottery_records(lottery_event, winner_guild_user, lottery_credits, le_dao, guild_user_dao,
                                      guild_dao, guild)

        # Cleanup
        await _cleanup_lottery(lottery_event, guild, channel)

        logger.info(f'Guild {guild.name}: Winner {discord_winner.name} won {lottery_credits} credits')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error ending lottery {lottery_event.id}: {e}')
    finally:
        le_dao.close()
        guild_dao.close()
        guild_user_dao.close()
        lp_dao.close()


async def _update_lottery_records(lottery_event, winner_guild_user, lottery_credits, le_dao, guild_user_dao, guild_dao,
                                  guild):
    """Update all database records for the lottery end."""
    try:
        # Update lottery event
        lottery_event.winner_id = winner_guild_user.user_id
        lottery_event.end_time = datetime.now(timezone.utc).replace(tzinfo=None)
        lottery_event.credits = lottery_credits
        le_dao.update_event(lottery_event)

        # Update winner's guild currency with global sync
        guild_user_dao.update_currency_with_global_sync(winner_guild_user.user_id, guild.id, lottery_credits)

        # Reset guild vault currency to 0
        guild_dao.update_vault_currency(guild.id, 0)

        logger.info(
            f'Guild {guild.name}: Updated lottery records - winner got {lottery_credits} credits, vault reset to 0')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error updating lottery records: {e}')
        raise


async def _send_lottery_reminder(lottery_event, guild, channel, remaining_time):
    """Send lottery reminder if it's time."""
    try:
        # Check if we need to post reminders every 10 minutes
        minutes_remaining = int(remaining_time.total_seconds() // 60)

        # Send reminder every 10 minutes (30, 20, 10 minutes remaining)
        if minutes_remaining > 0 and minutes_remaining % 10 == 0:
            # Check if we already sent a reminder for this time slot
            # (you might want to store this in database or cache to avoid spam)

            try:
                message = await channel.fetch_message(lottery_event.message_id)
                await channel.send(
                    f"## <a:pepesith:1165101386921418792> The lottery ends in {minutes_remaining} minutes! "
                    f"Enter here -> {message.jump_url}"
                )
                logger.info(f'Guild {guild.name}: Sent lottery reminder for {minutes_remaining} minutes remaining')
            except discord.NotFound:
                logger.warning(f'Guild {guild.name}: Lottery message {lottery_event.message_id} not found')
            except discord.HTTPException as e:
                logger.error(f'Guild {guild.name}: Failed to send lottery reminder: {e}')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error sending lottery reminder: {e}')

async def _cleanup_lottery(lottery_event, guild, channel):
    """Clean up lottery message and roles."""
    try:
        # Remove and delete lottery message
        try:
            message = await channel.fetch_message(lottery_event.message_id)
            await message.unpin()
            await message.delete()
        except discord.NotFound:
            logger.warning(f'Guild {guild.name}: Lottery message {lottery_event.message_id} already deleted')
        except discord.HTTPException as e:
            logger.error(f'Guild {guild.name}: Failed to delete lottery message: {e}')

        # Remove lottery role from all members
        lottery_role = discord.utils.get(guild.roles, name="LotteryParticipant")
        if lottery_role:
            for member in lottery_role.members:
                try:
                    await member.remove_roles(lottery_role, reason="Lottery ended")
                except discord.HTTPException as e:
                    logger.error(f'Guild {guild.name}: Failed to remove lottery role from {member.name}: {e}')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error during lottery cleanup: {e}')


async def _cleanup_empty_lottery(lottery_event, guild, channel, le_dao):
    """Clean up a lottery that had no participants."""
    try:
        # Mark lottery as ended with no winner
        lottery_event.end_time = datetime.now(timezone.utc).replace(tzinfo=None)
        lottery_event.winner_id = 0  # or None
        lottery_event.credits = 0
        le_dao.update_event(lottery_event)

        # Send message about no participants
        await channel.send("The lottery has ended with no participants. Better luck next time!")

        # Clean up message and roles
        await _cleanup_lottery(lottery_event, guild, channel)

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error cleaning up empty lottery: {e}')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error cleaning up empty lottery: {e}')