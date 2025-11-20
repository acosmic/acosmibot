#! /usr/bin/python3.10
import asyncio
from datetime import datetime
import logging
from Dao.UserDao import UserDao
from Dao.BankTransactionDao import BankTransactionDao
from Dao.GuildDao import GuildDao
from Dao.GlobalSettingsDao import GlobalSettingsDao

logger = logging.getLogger(__name__)


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await bank_interest_task(bot)


async def bank_interest_task(bot):
    """
    Bank interest task that pays interest on bank balances.
    Runs daily at midnight UTC for guilds with interest enabled.
    """
    await bot.wait_until_ready()

    last_daily_run = None
    last_weekly_run = None

    while not bot.is_closed():
        logger.debug('Running bank_interest_task check')

        now = datetime.utcnow()
        current_date = now.date()

        # Run at midnight UTC (hour 0, minute 0)
        if now.hour == 0 and now.minute == 0:
            # Daily interest check
            if last_daily_run != current_date:
                logger.info(f'Bank interest task executing daily run at {now}')
                try:
                    await _process_daily_interest(bot)
                    last_daily_run = current_date
                    logger.info("Daily bank interest processing completed")
                except Exception as e:
                    logger.error(f'Daily bank interest task error: {e}')

            # Weekly interest check (runs on Mondays - weekday 0)
            if now.weekday() == 0 and last_weekly_run != current_date:
                logger.info(f'Bank interest task executing weekly run at {now}')
                try:
                    await _process_weekly_interest(bot)
                    last_weekly_run = current_date
                    logger.info("Weekly bank interest processing completed")
                except Exception as e:
                    logger.error(f'Weekly bank interest task error: {e}')

        await asyncio.sleep(60)  # Check every minute


async def _process_daily_interest(bot):
    """
    Process daily interest for all guilds with daily interest enabled.
    Uses global interest settings from GlobalSettings table.
    """
    import json

    global_settings_dao = GlobalSettingsDao()
    guild_dao = GuildDao()
    try:
        # Get global interest settings
        interest_enabled_str = global_settings_dao.get_setting_value('economy.interest_enabled')
        interest_enabled = interest_enabled_str == 'true' if interest_enabled_str else False

        if not interest_enabled:
            logger.debug("Interest is globally disabled")
            return

        interest_interval_str = global_settings_dao.get_setting_value('economy.interest_interval')
        # Remove quotes if present (e.g., '"weekly"' -> 'weekly')
        interest_interval = interest_interval_str.strip('"') if interest_interval_str else 'weekly'

        if interest_interval != 'daily':
            logger.debug(f"Interest interval is {interest_interval}, skipping daily processing")
            return

        interest_rate_str = global_settings_dao.get_setting_value('economy.interest_rate_percent')
        interest_rate_percent = float(interest_rate_str) if interest_rate_str else 0.5
        # Convert percentage to decimal (0.5% -> 0.005)
        interest_rate = interest_rate_percent / 100

        guilds = guild_dao.get_all_guilds()

        if not guilds:
            logger.info("No active guilds found for daily interest processing")
            return

        total_processed = 0

        for guild_data in guilds:
            guild_id = guild_data.id  # Guild object attribute

            try:
                # Check if economy is enabled for this guild
                if guild_data.settings:
                    settings = json.loads(guild_data.settings) if isinstance(guild_data.settings, str) else guild_data.settings
                    economy_settings = settings.get('economy', {})

                    # Skip if guild has disabled economy
                    if not economy_settings.get('enabled', True):
                        continue

                # Process interest for this guild's users
                processed = await _apply_interest(guild_id, interest_rate, 'daily')
                total_processed += processed

                logger.info(f"Processed daily interest for guild {guild_id}: {processed} users")

            except Exception as e:
                logger.error(f"Error processing daily interest for guild {guild_id}: {e}")

        logger.info(f"Daily interest processing complete: {total_processed} total users processed")

    except Exception as e:
        logger.error(f'Error in daily interest processing: {e}')
        raise
    finally:
        global_settings_dao.close()
        guild_dao.close()


async def _process_weekly_interest(bot):
    """
    Process weekly interest for all guilds with weekly interest enabled.
    Uses global interest settings from GlobalSettings table.
    """
    import json

    global_settings_dao = GlobalSettingsDao()
    guild_dao = GuildDao()
    try:
        # Get global interest settings
        interest_enabled_str = global_settings_dao.get_setting_value('economy.interest_enabled')
        interest_enabled = interest_enabled_str == 'true' if interest_enabled_str else False

        if not interest_enabled:
            logger.debug("Interest is globally disabled")
            return

        interest_interval_str = global_settings_dao.get_setting_value('economy.interest_interval')
        # Remove quotes if present (e.g., '"weekly"' -> 'weekly')
        interest_interval = interest_interval_str.strip('"') if interest_interval_str else 'weekly'

        if interest_interval != 'weekly':
            logger.debug(f"Interest interval is {interest_interval}, skipping weekly processing")
            return

        interest_rate_str = global_settings_dao.get_setting_value('economy.interest_rate_percent')
        interest_rate_percent = float(interest_rate_str) if interest_rate_str else 0.5
        # Convert percentage to decimal (0.5% -> 0.005)
        interest_rate = interest_rate_percent / 100

        guilds = guild_dao.get_all_guilds()

        if not guilds:
            logger.info("No active guilds found for weekly interest processing")
            return

        total_processed = 0

        for guild_data in guilds:
            guild_id = guild_data.id  # Guild object attribute

            try:
                # Check if economy is enabled for this guild
                if guild_data.settings:
                    settings = json.loads(guild_data.settings) if isinstance(guild_data.settings, str) else guild_data.settings
                    economy_settings = settings.get('economy', {})

                    # Skip if guild has disabled economy
                    if not economy_settings.get('enabled', True):
                        continue

                # Process interest for this guild's users
                processed = await _apply_interest(guild_id, interest_rate, 'weekly')
                total_processed += processed

                logger.info(f"Processed weekly interest for guild {guild_id}: {processed} users")

            except Exception as e:
                logger.error(f"Error processing weekly interest for guild {guild_id}: {e}")

        logger.info(f"Weekly interest processing complete: {total_processed} total users processed")

    except Exception as e:
        logger.error(f'Error in weekly interest processing: {e}')
        raise
    finally:
        global_settings_dao.close()
        guild_dao.close()


async def _apply_interest(guild_id: int, interest_rate: float, interval: str) -> int:
    """
    Apply interest to all users with positive bank balances in a guild.

    Args:
        guild_id: Guild ID for transaction logging
        interest_rate: Interest rate as decimal (0.01 = 1%)
        interval: 'daily' or 'weekly'

    Returns:
        Number of users processed
    """
    user_dao = UserDao()
    bank_dao = BankTransactionDao()
    try:
        # Get all users with positive bank balance
        sql = """
            SELECT id, bank_balance
            FROM Users
            WHERE bank_balance > 0 AND is_bot = FALSE
        """

        results = user_dao.execute_query(sql)

        if not results:
            return 0

        processed_count = 0

        for user_id, bank_balance in results:
            try:
                # Calculate interest
                interest_amount = int(bank_balance * interest_rate)

                if interest_amount <= 0:
                    continue

                # Get current balance
                balance_before = bank_balance
                balance_after = balance_before + interest_amount

                # Update bank balance
                update_sql = """
                    UPDATE Users
                    SET bank_balance = bank_balance + %s
                    WHERE id = %s
                """
                user_dao.execute_query(update_sql, (interest_amount, user_id), commit=False)

                # Log transaction
                bank_dao.add_transaction(
                    user_id=user_id,
                    guild_id=guild_id,
                    transaction_type='interest',
                    amount=interest_amount,
                    fee=0,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    commit=False
                )

                # Commit both operations atomically
                user_dao.db.commit()

                processed_count += 1

                logger.debug(
                    f"Applied {interval} interest to user {user_id}: "
                    f"{interest_amount:,} credits ({interest_rate*100:.2f}%)"
                )

            except Exception as e:
                user_dao.db.rollback()
                logger.error(f"Error applying interest to user {user_id}: {e}")

        return processed_count

    except Exception as e:
        logger.error(f'Error in apply_interest: {e}')
        return 0
    finally:
        user_dao.close()
        bank_dao.close()
