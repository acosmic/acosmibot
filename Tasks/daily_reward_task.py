import asyncio
from datetime import datetime, timedelta
import logging
from Dao.GuildUserDao import GuildUserDao

logger = logging.getLogger(__name__)


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await daily_reward_task(bot)

async def daily_reward_task(bot):
    """Daily reward reset task that runs at UTC midnight for all guilds."""
    await bot.wait_until_ready()

    while not bot.is_closed():
        logger.info('Running daily_reward_task')

        # Check if it's UTC midnight (00:00)
        now = datetime.utcnow()
        if now.hour == 0 and now.minute == 0:
            logger.info('Daily reward task executing at UTC midnight')

            try:
                await _reset_daily_rewards_all_guilds(bot)
                logger.info("Daily reset completed for all guilds")

            except Exception as e:
                logger.error(f'Daily reward task error: {e}')

        await asyncio.sleep(60)


async def _reset_daily_rewards_all_guilds(bot):
    """Reset daily rewards for all guilds the bot is in."""
    guild_user_dao = GuildUserDao()

    # Process all guilds the bot is connected to
    for guild in bot.guilds:
        try:
            logger.info(f'Processing daily reset for guild: {guild.name} (ID: {guild.id})')
            await _reset_daily_rewards_for_guild(guild_user_dao, guild)

        except Exception as e:
            logger.error(f'Error processing guild {guild.name} (ID: {guild.id}): {e}')


async def _reset_daily_rewards_for_guild(guild_user_dao: GuildUserDao, guild):
    """Reset daily rewards for a specific guild."""
    # Reset daily status for all users in this guild
    guild_user_dao.reset_daily(guild.id)

    today = datetime.utcnow().date()
    processed_count = 0
    streak_resets = 0

    for member in guild.members:
        # Skip bots
        if member.bot:
            continue

        try:
            current_user = guild_user_dao.get_guild_user(member.id, guild.id)

            if current_user is None:
                # Skip users not in database
                continue

            processed_count += 1

            if current_user.last_daily is not None:
                # Handle datetime object properly
                if isinstance(current_user.last_daily, datetime):
                    last_daily_date = current_user.last_daily.date()
                else:
                    # If it's a string, parse it
                    last_daily_date = datetime.strptime(
                        str(current_user.last_daily), "%Y-%m-%d %H:%M:%S"
                    ).date()

                # Reset streak if user missed more than one day
                if last_daily_date < today - timedelta(days=1):
                    if current_user.streak > 0:
                        guild_user_dao.reset_streak(current_user.user_id, guild.id)
                        streak_resets += 1
                        logger.info(f'Guild {guild.name}: {current_user.name} streak reset')

        except Exception as e:
            logger.error(f'Error processing user {member.name} in guild {guild.name}: {e}')

    logger.info(f'Guild {guild.name}: Processed {processed_count} users, reset {streak_resets} streaks')

# import asyncio
# from datetime import datetime, timedelta
# import logging
# from Dao.GuildUserDao import GuildUserDao  # adjust path if needed
#
# logger = logging.getLogger(__name__)
#
# async def daily_reward_task(bot):
#     """Good morning EU task."""
#     await bot.wait_until_ready()
#     channel = bot.get_channel(1155577095787917384)
#     search_term = 'monkey'
#     logger.info(f'goodmorning gif search_term: {search_term}')
#
#     while not bot.is_closed():
#         logger.info('daily_reward_task')
#         if datetime.now().hour == 2 and datetime.now().minute == 50:
#             logger.info('gm_eu_task running at 2:50am which is 7:50am in EU')
#             try:
#                 guild_user_dao = GuildUserDao()
#                 guild_user_dao.reset_daily()
#
#                 today = datetime.now().date()
#                 guild = channel.guild
#                 for member in guild.members:
#                     current_user = guild_user_dao.get_guild_user(member.id, guild.id)
#                     if current_user.last_daily is not None:
#                         last_daily_date = datetime.strptime(
#                             str(current_user.last_daily), "%Y-%m-%d %H:%M:%S"
#                         ).date()
#                         if last_daily_date < today - timedelta(days=1):
#                             if current_user.streak > 0:
#                                 guild_user_dao.reset_streak(current_user.id)
#                                 logger.info(f'{current_user.discord_username} streak reset')
#
#             except Exception as e:
#                 logger.error(f'daily_reward_task error: {e}')
#
#             logger.info("DAILY RESET FOR ALL USERS")
#
#         await asyncio.sleep(60)
