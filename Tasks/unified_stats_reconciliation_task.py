#! /usr/bin/python3.10
"""
Unified Stats Reconciliation Task

Reconciles all global user statistics from guild-specific data.
Runs every 6 hours to keep stats synchronized.

Reconciles:
- total_messages: Sum of messages_sent across all active guilds
- total_reactions: Sum of reactions_sent across all active guilds
- global_exp & global_level: Sum of exp across guilds with level recalculation
- total_currency: Sum of guild currencies PLUS bank_balance (total wealth)

This replaces the old currency_reconciliation_task.py with a more comprehensive solution.
"""

import asyncio
import logging
from Dao.UserDao import UserDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


async def start_task(bot):
    """Entry point for unified stats reconciliation task"""
    await unified_stats_reconciliation_task(bot)


async def unified_stats_reconciliation_task(bot):
    """
    Reconcile all global user statistics from guild data.
    Runs every 6 hours.
    """
    await bot.wait_until_ready()

    # Wait 5 minutes before first run (grace period for bot startup)
    logger.info("Unified stats reconciliation task started - waiting 5 minutes before first run")
    await asyncio.sleep(300)

    while not bot.is_closed():
        try:
            await reconcile_all_stats()
        except Exception as e:
            logger.error(f"Error in unified stats reconciliation: {e}", exc_info=True)

        # Run every 6 hours (21,600 seconds)
        await asyncio.sleep(21600)


async def reconcile_all_stats():
    """
    Reconcile all global statistics from guild-specific data.
    """
    logger.info("=== Starting unified stats reconciliation ===")

    user_dao = UserDao()
    stats = {
        'total_messages': 0,
        'total_reactions': 0,
        'global_exp': 0,
        'total_currency': 0
    }

    try:
        # 1. Reconcile total_messages
        stats['total_messages'] = await reconcile_total_messages(user_dao)

        # 2. Reconcile total_reactions
        stats['total_reactions'] = await reconcile_total_reactions(user_dao)

        # 3. Reconcile global_exp and global_level
        stats['global_exp'] = await reconcile_global_exp(user_dao)

        # 4. Reconcile total_currency (guild + bank)
        stats['total_currency'] = await reconcile_total_currency(user_dao)

        # Log summary
        logger.info(
            f"=== Stats reconciliation complete ===\n"
            f"  - Messages corrected: {stats['total_messages']} users\n"
            f"  - Reactions corrected: {stats['total_reactions']} users\n"
            f"  - Exp/Level corrected: {stats['global_exp']} users\n"
            f"  - Currency corrected: {stats['total_currency']} users"
        )

    except Exception as e:
        logger.error(f"Error during stats reconciliation: {e}", exc_info=True)


async def reconcile_total_messages(user_dao: UserDao) -> int:
    """
    Reconcile Users.total_messages from GuildUsers.messages_sent.

    Returns:
        Number of users affected
    """
    sql = """
        UPDATE Users u
        LEFT JOIN (
            SELECT user_id, COALESCE(SUM(messages_sent), 0) as total
            FROM GuildUsers
            WHERE is_active = TRUE
            GROUP BY user_id
        ) gu ON u.id = gu.user_id
        SET u.total_messages = COALESCE(gu.total, 0)
        WHERE u.is_bot = FALSE
        AND u.total_messages != COALESCE(gu.total, 0)
    """

    try:
        # Use direct database access to get rowcount
        cursor = user_dao.db.mydb.cursor()
        cursor.execute(sql)
        user_dao.db.mydb.commit()
        affected = cursor.rowcount
        cursor.close()
        logger.info(f"Reconciled total_messages for {affected} users")
        return affected
    except Exception as e:
        logger.error(f"Error reconciling total_messages: {e}")
        return 0


async def reconcile_total_reactions(user_dao: UserDao) -> int:
    """
    Reconcile Users.total_reactions from GuildUsers.reactions_sent.

    Returns:
        Number of users affected
    """
    sql = """
        UPDATE Users u
        LEFT JOIN (
            SELECT user_id, COALESCE(SUM(reactions_sent), 0) as total
            FROM GuildUsers
            WHERE is_active = TRUE
            GROUP BY user_id
        ) gu ON u.id = gu.user_id
        SET u.total_reactions = COALESCE(gu.total, 0)
        WHERE u.is_bot = FALSE
        AND u.total_reactions != COALESCE(gu.total, 0)
    """

    try:
        # Use direct database access to get rowcount
        cursor = user_dao.db.mydb.cursor()
        cursor.execute(sql)
        user_dao.db.mydb.commit()
        affected = cursor.rowcount
        cursor.close()
        logger.info(f"Reconciled total_reactions for {affected} users")
        return affected
    except Exception as e:
        logger.error(f"Error reconciling total_reactions: {e}")
        return 0


async def reconcile_global_exp(user_dao: UserDao) -> int:
    """
    Reconcile Users.global_exp and global_level from GuildUsers.exp.
    Level formula: level = floor(sqrt(exp / 100))

    Returns:
        Number of users affected
    """
    sql = """
        UPDATE Users u
        LEFT JOIN (
            SELECT user_id, COALESCE(SUM(exp), 0) as total
            FROM GuildUsers
            WHERE is_active = TRUE
            GROUP BY user_id
        ) gu ON u.id = gu.user_id
        SET u.global_exp = COALESCE(gu.total, 0),
            u.global_level = FLOOR(SQRT(COALESCE(gu.total, 0) / 100))
        WHERE u.is_bot = FALSE
        AND (
            u.global_exp != COALESCE(gu.total, 0)
            OR u.global_level != FLOOR(SQRT(COALESCE(gu.total, 0) / 100))
        )
    """

    try:
        # Use direct database access to get rowcount
        cursor = user_dao.db.mydb.cursor()
        cursor.execute(sql)
        user_dao.db.mydb.commit()
        affected = cursor.rowcount
        cursor.close()
        logger.info(f"Reconciled global_exp and global_level for {affected} users")
        return affected
    except Exception as e:
        logger.error(f"Error reconciling global_exp: {e}")
        return 0


async def reconcile_total_currency(user_dao: UserDao) -> int:
    """
    Reconcile Users.total_currency from GuildUsers.currency + Users.bank_balance.
    This represents total wealth (guild wallets + bank).

    Returns:
        Number of users affected
    """
    sql = """
        UPDATE Users u
        LEFT JOIN (
            SELECT user_id, COALESCE(SUM(currency), 0) as total
            FROM GuildUsers
            WHERE is_active = TRUE
            GROUP BY user_id
        ) gu ON u.id = gu.user_id
        SET u.total_currency = COALESCE(gu.total, 0) + u.bank_balance
        WHERE u.is_bot = FALSE
        AND u.total_currency != (COALESCE(gu.total, 0) + u.bank_balance)
    """

    try:
        # Use direct database access to get rowcount
        cursor = user_dao.db.mydb.cursor()
        cursor.execute(sql)
        user_dao.db.mydb.commit()
        affected = cursor.rowcount
        cursor.close()
        logger.info(f"Reconciled total_currency for {affected} users")
        return affected
    except Exception as e:
        logger.error(f"Error reconciling total_currency: {e}")
        return 0
