"""
DEPRECATED: This task has been replaced by unified_stats_reconciliation_task.py

The new task reconciles:
- total_currency (guild + bank)
- total_messages
- total_reactions
- global_exp & global_level

And runs every 6 hours instead of twice daily.

This file is kept for reference only and is no longer loaded by the bot.
Date deprecated: 2025-11-04
"""

import asyncio
from datetime import datetime
import logging
from Dao.UserDao import UserDao

logger = logging.getLogger(__name__)


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await currency_reconciliation_task(bot)


async def currency_reconciliation_task(bot):
    """Currency reconciliation task that runs twice daily (6 AM and 6 PM UTC)."""
    await bot.wait_until_ready()

    while not bot.is_closed():
        logger.info('Running currency_reconciliation_task check')

        # Run at 6 AM (hour 6) and 6 PM (hour 18) UTC
        now = datetime.utcnow()
        if (now.hour == 6 or now.hour == 18) and now.minute == 0:
            logger.info(f'Currency reconciliation task executing at {now.hour}:00 UTC')

            try:
                await _reconcile_total_currency()
                logger.info("Currency reconciliation completed")

            except Exception as e:
                logger.error(f'Currency reconciliation task error: {e}')

        await asyncio.sleep(60)  # Check every minute


async def _reconcile_total_currency():
    """
    Reconcile Users.total_currency with the sum of GuildUsers.currency.
    This ensures global currency totals are accurate.
    """
    user_dao = UserDao()
    try:
        # First, get count of users that need reconciliation (for logging)
        check_sql = """
            SELECT COUNT(*) as count
            FROM Users u
            LEFT JOIN (
                SELECT user_id, COALESCE(SUM(currency), 0) as total
                FROM GuildUsers
                WHERE is_active = TRUE
                GROUP BY user_id
            ) gu ON u.id = gu.user_id
            WHERE u.is_bot = FALSE
            AND u.total_currency != COALESCE(gu.total, 0)
        """

        result = user_dao.execute_query(check_sql)
        discrepancies_count = result[0][0] if result and result[0] else 0

        if discrepancies_count > 0:
            logger.info(f'Found {discrepancies_count} users with currency discrepancies, reconciling...')

            # Execute reconciliation update
            update_sql = """
                UPDATE Users u
                LEFT JOIN (
                    SELECT user_id, COALESCE(SUM(currency), 0) as total
                    FROM GuildUsers
                    WHERE is_active = TRUE
                    GROUP BY user_id
                ) gu ON u.id = gu.user_id
                SET u.total_currency = COALESCE(gu.total, 0)
                WHERE u.is_bot = FALSE
            """

            user_dao.execute_query(update_sql, commit=True)
            logger.info(f'Successfully reconciled {discrepancies_count} users\' total currency')
        else:
            logger.info('No currency discrepancies found, all totals are in sync')

    except Exception as e:
        logger.error(f'Error reconciling total currency: {e}')
        raise
    finally:
        user_dao.close()
