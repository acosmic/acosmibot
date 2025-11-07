#! /usr/bin/python3.10
"""
Unified Stats Reconciliation Task

Reconciles all global user statistics from guild-specific data.
Runs every 6 hours to keep stats synchronized.

Reconciles:
- Missing Users: Creates User records for orphaned GuildUsers and Games records
- total_messages: Sum of messages_sent across all active guilds
- total_reactions: Sum of reactions_sent across all active guilds
- global_exp & global_level: Sum of exp across guilds with level recalculation
- total_currency: Sum of guild currencies PLUS bank_balance (total wealth)

This replaces the old currency_reconciliation_task.py with a more comprehensive solution.
"""

import asyncio
import logging
from datetime import datetime
from Dao.UserDao import UserDao
from Entities.User import User
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
        'missing_users_created': 0,
        'total_messages': 0,
        'total_reactions': 0,
        'global_exp': 0,
        'total_currency': 0
    }

    try:
        # 0. Create missing users from orphaned GuildUsers and Games records
        stats['missing_users_created'] = await create_missing_users(user_dao)

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
            f"  - Missing users created: {stats['missing_users_created']}\n"
            f"  - Messages corrected: {stats['total_messages']} users\n"
            f"  - Reactions corrected: {stats['total_reactions']} users\n"
            f"  - Exp/Level corrected: {stats['global_exp']} users\n"
            f"  - Currency corrected: {stats['total_currency']} users"
        )

    except Exception as e:
        logger.error(f"Error during stats reconciliation: {e}", exc_info=True)


async def create_missing_users(user_dao: UserDao) -> int:
    """
    Create User records for any orphaned users in GuildUsers or Games tables.
    This ensures all users with activity have corresponding User table entries.

    Returns:
        Number of users created
    """
    created_count = 0

    try:
        # Find user IDs in GuildUsers that don't exist in Users
        sql_guild_users = """
            SELECT DISTINCT gu.user_id
            FROM GuildUsers gu
            LEFT JOIN Users u ON gu.user_id = u.id
            WHERE u.id IS NULL
        """

        # Find user IDs in Games that don't exist in Users
        sql_games = """
            SELECT DISTINCT g.user_id
            FROM Games g
            LEFT JOIN Users u ON g.user_id = u.id
            WHERE u.id IS NULL
        """

        # Execute queries to get missing user IDs
        cursor = user_dao.db.mydb.cursor()

        cursor.execute(sql_guild_users)
        guild_user_ids = [row[0] for row in cursor.fetchall()]

        cursor.execute(sql_games)
        games_user_ids = [row[0] for row in cursor.fetchall()]

        cursor.close()

        # Combine and deduplicate
        missing_user_ids = set(guild_user_ids) | set(games_user_ids)

        if not missing_user_ids:
            logger.info("No missing users found")
            return 0

        logger.info(f"Found {len(missing_user_ids)} users missing from Users table")

        # Create User records for each missing user ID
        formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        users_to_create = []

        for user_id in missing_user_ids:
            # Create a minimal User record with default values
            # We use the user_id as a placeholder for discord_username
            new_user = User(
                id=user_id,
                discord_username=f"user_{user_id}",  # Placeholder username
                global_name=None,
                avatar_url=None,
                is_bot=False,
                global_exp=0,
                global_level=0,
                total_currency=0,
                bank_balance=0,
                daily_transfer_amount=0,
                last_transfer_reset=None,
                total_messages=0,
                total_reactions=0,
                account_created=formatted_date,
                first_seen=formatted_date,
                last_seen=formatted_date,
                privacy_settings=None,
                global_settings=None
            )
            users_to_create.append(new_user)

        # Bulk upsert the users
        if users_to_create:
            success = user_dao.bulk_upsert_users(users_to_create)
            if success:
                created_count = len(users_to_create)
                logger.info(f"Successfully created {created_count} missing user records")
            else:
                logger.error(f"Failed to create {len(users_to_create)} missing user records")

        return created_count

    except Exception as e:
        logger.error(f"Error creating missing users: {e}", exc_info=True)
        return 0


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
