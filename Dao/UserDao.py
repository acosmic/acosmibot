from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime
from database import Database
from Dao.BaseDao import BaseDao
from Entities.User import User
from dotenv import load_dotenv
import os
import logging


class UserDao(BaseDao[User]):
    """
    Data Access Object for User entities.
    Provides methods to interact with the Users table in the database.
    Handles global user data that persists across all guilds.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the UserDao with connection parameters.

        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(User, "Users", db)

        # Create the table if it doesn't exist
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> None:
        """
        Create the Users table if it doesn't exist.
        """
        create_table_sql = '''
                           CREATE TABLE IF NOT EXISTS Users \
                           ( \
                               id \
                               BIGINT \
                               PRIMARY \
                               KEY, \
                               discord_username \
                               VARCHAR \
                           ( \
                               255 \
                           ) NOT NULL,
                               global_name VARCHAR \
                           ( \
                               255 \
                           ),
                               avatar_url TEXT,
                               is_bot BOOLEAN DEFAULT FALSE,
                               global_exp INT DEFAULT 0,
                               global_level INT DEFAULT 0,
                               total_currency INT DEFAULT 0,
                               bank_balance INT DEFAULT 0,
                               daily_transfer_amount INT DEFAULT 0,
                               last_transfer_reset DATE,
                               last_interest_payout_date DATE,
                               total_messages INT DEFAULT 0,
                               total_reactions INT DEFAULT 0,
                               account_created DATETIME,
                               first_seen DATETIME,
                               last_seen DATETIME,
                               privacy_settings JSON,
                               global_settings JSON,
                               INDEX idx_global_exp (global_exp DESC),
                               INDEX idx_global_level (global_level DESC),
                               INDEX idx_total_currency (total_currency DESC),
                               INDEX idx_bank_balance (bank_balance DESC)
                               ) \
                           '''
        self.create_table_if_not_exists(create_table_sql)

    def add_user(self, new_user: User) -> bool:
        """
        Add a new user to the database.

        Args:
            new_user (User): User to add

        Returns:
            bool: True if successful, False otherwise
        """
        sql = '''
              INSERT INTO Users (id, \
                                 discord_username, \
                                 global_name, \
                                 avatar_url, \
                                 is_bot, \
                                 global_exp, \
                                 global_level, \
                                 total_currency, \
                                 bank_balance, \
                                 daily_transfer_amount, \
                                 last_transfer_reset, \
                                 last_interest_payout_date, \
                                 total_messages, \
                                 total_reactions, \
                                 account_created, \
                                 first_seen, \
                                 last_seen, \
                                 privacy_settings, \
                                 global_settings) \
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) \
              '''
        values = (
            new_user.id,
            new_user.discord_username,
            new_user.global_name,
            new_user.avatar_url,
            new_user.is_bot,
            new_user.global_exp,
            new_user.global_level,
            new_user.total_currency,
            new_user.bank_balance,
            new_user.daily_transfer_amount,
            new_user.last_transfer_reset,
            new_user.last_interest_payout_date,
            new_user.total_messages,
            new_user.total_reactions,
            new_user.account_created,
            new_user.first_seen,
            new_user.last_seen,
            new_user.privacy_settings,
            new_user.global_settings
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding user: {e}")
            return False

    def update_user(self, updated_user: User) -> bool:
        """
        Update an existing user in the database.

        Args:
            updated_user (User): User to update

        Returns:
            bool: True if successful, False otherwise
        """
        sql = '''
              UPDATE Users
              SET discord_username = %s,
                  global_name      = %s,
                  avatar_url       = %s,
                  is_bot           = %s,
                  global_exp       = %s,
                  global_level     = %s,
                  total_currency   = %s,
                  bank_balance     = %s,
                  daily_transfer_amount = %s,
                  last_transfer_reset = %s,
                  last_interest_payout_date = %s,
                  total_messages   = %s,
                  total_reactions  = %s,
                  account_created  = %s,
                  first_seen       = %s,
                  last_seen        = %s,
                  privacy_settings = %s,
                  global_settings  = %s
              WHERE id = %s \
              '''
        values = (
            updated_user.discord_username,
            updated_user.global_name,
            updated_user.avatar_url,
            updated_user.is_bot,
            updated_user.global_exp,
            updated_user.global_level,
            updated_user.total_currency,
            updated_user.bank_balance,
            updated_user.daily_transfer_amount,
            updated_user.last_transfer_reset,
            updated_user.last_interest_payout_date,
            updated_user.total_messages,
            updated_user.total_reactions,
            updated_user.account_created,
            updated_user.first_seen,
            updated_user.last_seen,
            updated_user.privacy_settings,
            updated_user.global_settings,
            updated_user.id,
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating user: {e}")
            return False

    def get_user(self, id: int) -> Optional[User]:
        sql = '''SELECT id, discord_username, global_name, avatar_url, is_bot,
                        global_exp, global_level, total_currency, bank_balance,
                        daily_transfer_amount, last_transfer_reset, last_interest_payout_date,
                        total_messages, total_reactions, account_created, first_seen,
                        last_seen, privacy_settings, global_settings
                 FROM Users WHERE id = %s'''

        try:
            result = self.execute_query(sql, (id,))

            if result and len(result) > 0:
                user_data = result[0]
                user = User(
                    id=user_data[0],
                    discord_username=user_data[1],
                    global_name=user_data[2],
                    avatar_url=user_data[3],
                    is_bot=user_data[4],
                    global_exp=user_data[5],
                    global_level=user_data[6],
                    total_currency=user_data[7],
                    bank_balance=user_data[8],
                    daily_transfer_amount=user_data[9],
                    last_transfer_reset=user_data[10],
                    last_interest_payout_date=user_data[11],
                    total_messages=user_data[12],
                    total_reactions=user_data[13],
                    account_created=user_data[14],
                    first_seen=user_data[15],
                    last_seen=user_data[16],
                    privacy_settings=user_data[17],
                    global_settings=user_data[18]
                )
                return user
            return None

        except Exception as e:
            self.logger.error(f"Error getting user: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by their Discord username.

        Args:
            username (str): Discord username

        Returns:
            Optional[User]: User if found, None otherwise
        """
        sql = '''SELECT id, discord_username, global_name, avatar_url, is_bot,
                        global_exp, global_level, total_currency, bank_balance,
                        daily_transfer_amount, last_transfer_reset, last_interest_payout_date,
                        total_messages, total_reactions, account_created, first_seen,
                        last_seen, privacy_settings, global_settings
                 FROM Users WHERE discord_username = %s'''

        try:
            result = self.execute_query(sql, (username,))

            if result and len(result) > 0:
                user_data = result[0]
                user = User(
                    id=user_data[0],
                    discord_username=user_data[1],
                    global_name=user_data[2],
                    avatar_url=user_data[3],
                    is_bot=user_data[4],
                    global_exp=user_data[5],
                    global_level=user_data[6],
                    total_currency=user_data[7],
                    bank_balance=user_data[8],
                    daily_transfer_amount=user_data[9],
                    last_transfer_reset=user_data[10],
                    last_interest_payout_date=user_data[11],
                    total_messages=user_data[12],
                    total_reactions=user_data[13],
                    account_created=user_data[14],
                    first_seen=user_data[15],
                    last_seen=user_data[16],
                    privacy_settings=user_data[17],
                    global_settings=user_data[18]
                )
                return user
            return None

        except Exception as e:
            self.logger.error(f"Error getting user by username: {e}")
            return None

    def get_user_rank_by_global_exp(self, id: int) -> Optional[Tuple]:
        """
        Get a user's rank based on global experience points.

        Args:
            id (int): User ID

        Returns:
            Optional[Tuple]: User data with rank if found, None otherwise
        """
        rank_query = '''
                     SELECT id, \
                            discord_username, \
                            global_name, \
                            avatar_url, \
                            is_bot, \
                            global_exp, \
                            global_level, \
                            total_currency, \
                            total_messages, \
                            total_reactions, \
                            account_created, \
                            first_seen, \
                            last_seen, \
                            privacy_settings, \
                            global_settings, \
                            (SELECT COUNT(*) + 1 \
                             FROM Users u2 \
                             WHERE u2.global_exp > u1.global_exp AND u2.is_bot = FALSE) AS user_rank
                     FROM Users u1
                     WHERE id = %s; \
                     '''

        try:
            result = self.execute_query(rank_query, (id,))
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Error getting user rank by global exp: {e}")
            return None

    def get_top_users_by_global_level(self, limit: int = 10) -> List[Tuple]:
        """
        Get the top users by global level.

        Args:
            limit (int, optional): Maximum number of users to return. Defaults to 5.

        Returns:
            List[Tuple]: List of top users
        """
        sql = '''
              SELECT id, discord_username, global_name, global_level, global_exp
              FROM Users
              WHERE is_bot = FALSE
              ORDER BY global_level DESC, global_exp DESC
                  LIMIT %s \
              '''

        try:
            return self.execute_query(sql, (limit,)) or []
        except Exception as e:
            self.logger.error(f"Error getting top users by global level: {e}")
            return []

    def get_user_rank_by_currency(self, id: int) -> Optional[Tuple]:
        """
        Get a user's rank based on total currency.

        Args:
            id (int): User ID

        Returns:
            Optional[Tuple]: User data with rank if found, None otherwise
        """
        rank_query = '''
                     SELECT id, \
                            discord_username, \
                            global_name, \
                            avatar_url, \
                            is_bot, \
                            global_exp, \
                            global_level, \
                            total_currency, \
                            total_messages, \
                            total_reactions, \
                            account_created, \
                            first_seen, \
                            last_seen, \
                            privacy_settings, \
                            global_settings, \
                            (SELECT COUNT(*) + 1 \
                             FROM Users u2 \
                             WHERE u2.total_currency > u1.total_currency AND u2.is_bot = FALSE) AS user_rank
                     FROM Users u1
                     WHERE id = %s; \
                     '''

        try:
            result = self.execute_query(rank_query, (id,))
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Error getting user rank by currency: {e}")
            return None

    def get_top_users_by_global_exp(self, limit: int = 10) -> List[Tuple]:
        """
        Get the top users by global experience.

        Args:
            limit (int, optional): Maximum number of users to return. Defaults to 5.

        Returns:
            List[Tuple]: List of top users
        """
        sql = '''
              SELECT id, discord_username, global_name, global_exp, global_level
              FROM Users
              WHERE is_bot = FALSE
              ORDER BY global_exp DESC
                  LIMIT %s \
              '''

        try:
            return self.execute_query(sql, (limit,)) or []
        except Exception as e:
            self.logger.error(f"Error getting top users by global exp: {e}")
            return []

    def get_top_users_by_currency(self, limit: int = 10) -> List[Tuple]:
        """
        Get the top users by total currency.

        Args:
            limit (int, optional): Maximum number of users to return. Defaults to 10.

        Returns:
            List[Tuple]: List of top users (id, discord_username, global_name, total_currency, global_level)
        """
        sql = '''
              SELECT id, discord_username, global_name, total_currency, global_level
              FROM Users
              WHERE is_bot = FALSE
              ORDER BY total_currency DESC
                  LIMIT %s \
              '''

        try:
            return self.execute_query(sql, (limit,)) or []
        except Exception as e:
            self.logger.error(f"Error getting top users by currency: {e}")
            return []

    def get_top_users_by_messages(self, limit: int = 5) -> List[Tuple]:
        """
        Get the top users by total messages.

        Args:
            limit (int, optional): Maximum number of users to return. Defaults to 5.

        Returns:
            List[Tuple]: List of top users
        """
        sql = '''
              SELECT id, discord_username, global_name, total_messages
              FROM Users
              WHERE is_bot = FALSE
              ORDER BY total_messages DESC
                  LIMIT %s \
              '''

        try:
            return self.execute_query(sql, (limit,)) or []
        except Exception as e:
            self.logger.error(f"Error getting top users by messages: {e}")
            return []

    def get_total_messages(self) -> int:
        """
        Get the total number of messages sent by all users.

        Returns:
            int: Total number of messages
        """
        sql = 'SELECT SUM(total_messages) FROM Users WHERE is_bot = FALSE'

        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total messages: {e}")
            return 0

    def get_total_reactions(self) -> int:
        """
        Get the total number of reactions sent by all users.

        Returns:
            int: Total number of reactions
        """
        sql = 'SELECT SUM(total_reactions) FROM Users WHERE is_bot = FALSE'

        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total reactions: {e}")
            return 0

    def get_total_currency(self) -> int:
        """
        Get the total amount of currency held by all users.

        Returns:
            int: Total currency
        """
        sql = 'SELECT SUM(total_currency) FROM Users WHERE is_bot = FALSE'

        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total currency: {e}")
            return 0

    def get_total_global_exp(self) -> int:
        """
        Get the total amount of global experience points earned by all users.

        Returns:
            int: Total global experience points
        """
        sql = 'SELECT SUM(global_exp) FROM Users WHERE is_bot = FALSE'

        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total global experience: {e}")
            return 0

    def get_total_users(self) -> int:
        """
        Get the total number of users (excluding bots).

        Returns:
            int: Total number of users
        """
        sql = 'SELECT COUNT(*) FROM Users WHERE is_bot = FALSE'

        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total users: {e}")
            return 0

    def get_total_active_users(self, hours: int = 24) -> int:
        """
        Get the total number of active users in the last specified hours.

        Args:
            hours (int, optional): Number of hours to look back. Defaults to 24.

        Returns:
            int: Total number of active users
        """
        sql = '''
              SELECT COUNT(*)
              FROM Users
              WHERE last_seen > DATE_SUB(NOW(), INTERVAL %s HOUR) \
                AND is_bot = FALSE \
              '''

        try:
            result = self.execute_query(sql, (hours,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total active users: {e}")
            return 0

    def get_users_by_date_range(self, start_date: datetime, end_date: datetime) -> List[User]:
        """
        Get users who first joined within a date range.

        Args:
            start_date (datetime): Start date
            end_date (datetime): End date

        Returns:
            List[User]: List of users
        """
        sql = '''
              SELECT id, discord_username, global_name, avatar_url, is_bot,
                     global_exp, global_level, total_currency, bank_balance,
                     daily_transfer_amount, last_transfer_reset, last_interest_payout_date,
                     total_messages, total_reactions, account_created, first_seen,
                     last_seen, privacy_settings, global_settings
              FROM Users
              WHERE first_seen BETWEEN %s AND %s \
                AND is_bot = FALSE
              ORDER BY first_seen DESC \
              '''

        try:
            results = self.execute_query(sql, (start_date, end_date))

            users = []
            if results:
                for user_data in results:
                    users.append(User(
                        id=user_data[0],
                        discord_username=user_data[1],
                        global_name=user_data[2],
                        avatar_url=user_data[3],
                        is_bot=user_data[4],
                        global_exp=user_data[5],
                        global_level=user_data[6],
                        total_currency=user_data[7],
                        bank_balance=user_data[8],
                        daily_transfer_amount=user_data[9],
                        last_transfer_reset=user_data[10],
                        last_interest_payout_date=user_data[11],
                        total_messages=user_data[12],
                        total_reactions=user_data[13],
                        account_created=user_data[14],
                        first_seen=user_data[15],
                        last_seen=user_data[16],
                        privacy_settings=user_data[17],
                        global_settings=user_data[18]
                    ))

            return users

        except Exception as e:
            self.logger.error(f"Error getting users by date range: {e}")
            return []

    def update_last_seen(self, user_id: int) -> bool:
        """
        Update the last_seen timestamp for a user.

        Args:
            user_id (int): User ID

        Returns:
            bool: True if successful, False otherwise
        """
        sql = 'UPDATE Users SET last_seen = NOW() WHERE id = %s'

        try:
            self.execute_query(sql, (user_id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating last seen: {e}")
            return False

    def increment_user_stats(self, user_id: int, global_exp_gain: int = 0, currency_gain: int = 0,
                             messages_gain: int = 0, reactions_gain: int = 0) -> bool:
        """
        Increment user statistics.

        Args:
            user_id (int): User ID
            global_exp_gain (int, optional): Global experience to add. Defaults to 0.
            currency_gain (int, optional): Currency to add. Defaults to 0.
            messages_gain (int, optional): Messages to add. Defaults to 0.
            reactions_gain (int, optional): Reactions to add. Defaults to 0.

        Returns:
            bool: True if successful, False otherwise
        """
        sql = '''
              UPDATE Users
              SET global_exp      = global_exp + %s,
                  total_currency  = total_currency + %s,
                  total_messages  = total_messages + %s,
                  total_reactions = total_reactions + %s,
                  last_seen       = NOW()
              WHERE id = %s \
              '''

        try:
            self.execute_query(sql, (global_exp_gain, currency_gain, messages_gain, reactions_gain, user_id), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error incrementing user stats: {e}")
            return False

    def get_or_create_user_from_discord(self, discord_user) -> Optional[User]:
        """
        Get existing user or create new one from Discord user object.

        Args:
            discord_user: Discord user object (discord.User or discord.Member)

        Returns:
            Optional[User]: User object or None on error
        """
        try:
            # First try to get existing user
            existing_user = self.get_user(discord_user.id)
            if existing_user:
                # Update basic info in case it changed
                existing_user._discord_username = discord_user.name
                existing_user._global_name = getattr(discord_user, 'global_name', discord_user.name)
                existing_user._avatar_url = str(
                    discord_user.avatar.url) if discord_user.avatar else existing_user.avatar_url
                # existing_user._last_seen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.update_user(existing_user)
                return existing_user

            # Create new user
            formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                account_created = discord_user.created_at.strftime(
                    "%Y-%m-%d %H:%M:%S") if discord_user.created_at else formatted_date
            except Exception:
                account_created = formatted_date

            new_user = User(
                id=discord_user.id,
                discord_username=discord_user.name,
                global_name=getattr(discord_user, 'global_name', discord_user.name),
                avatar_url=str(discord_user.avatar.url) if discord_user.avatar else None,
                is_bot=discord_user.bot,
                global_exp=0,
                global_level=0,
                total_currency=0,
                bank_balance=0,
                daily_transfer_amount=0,
                last_transfer_reset=None,
                total_messages=0,
                total_reactions=0,
                account_created=account_created,
                first_seen=formatted_date,
                last_seen=formatted_date,
                privacy_settings=None,
                global_settings=None
            )

            if self.add_user(new_user):
                self.logger.info(f"Created new global user: {discord_user.name}")
                return new_user
            else:
                # add_user failed - could be duplicate key (race condition)
                # Try to get the user one more time
                existing_user = self.get_user(discord_user.id)
                if existing_user:
                    self.logger.info(f"User {discord_user.name} already existed (race condition)")
                    return existing_user
                else:
                    self.logger.error(f"Failed to create global user: {discord_user.name}")
                    return None

        except Exception as e:
            self.logger.error(f"Error getting/creating global user {discord_user.name}: {e}")
            return None

    def ensure_user_exists(self, discord_user) -> bool:
        """
        Ensure a user exists in the database, create if not.

        Args:
            discord_user: Discord user object

        Returns:
            bool: True if user exists/was created, False on error
        """
        try:
            user = self.get_or_create_user_from_discord(discord_user)
            return user is not None
        except Exception as e:
            self.logger.error(f"Error ensuring user exists for {discord_user.name}: {e}")
            return False

    def bulk_upsert_users(self, users: List[User]) -> bool:
        """
        Bulk insert or update users in a single transaction.
        Uses INSERT ... ON DUPLICATE KEY UPDATE for efficiency.

        Args:
            users (List[User]): List of users to upsert

        Returns:
            bool: True if successful, False otherwise
        """
        if not users:
            return True

        sql = '''
              INSERT INTO Users (id, discord_username, global_name, avatar_url, is_bot,
                                 global_exp, global_level, total_currency, bank_balance,
                                 daily_transfer_amount, last_transfer_reset, last_interest_payout_date, 
                                 total_messages, total_reactions, account_created, first_seen, last_seen,
                                 privacy_settings, global_settings)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
              ON DUPLICATE KEY UPDATE
                  discord_username = VALUES(discord_username),
                  global_name = VALUES(global_name),
                  avatar_url = COALESCE(VALUES(avatar_url), avatar_url),
                  last_seen = VALUES(last_seen)
              '''

        try:
            # Prepare all values at once
            values_list = [
                (
                    user.id,
                    user.discord_username,
                    user.global_name,
                    user.avatar_url,
                    user.is_bot,
                    user.global_exp,
                    user.global_level,
                    user.total_currency,
                    user.bank_balance,
                    user.daily_transfer_amount,
                    user.last_transfer_reset,
                    user.last_interest_payout_date,
                    user.total_messages,
                    user.total_reactions,
                    user.account_created,
                    user.first_seen,
                    user.last_seen,
                    user.privacy_settings,
                    user.global_settings
                )
                for user in users
            ]

            # Execute with executemany for bulk insert
            self.execute_many(sql, values_list, commit=True)
            self.logger.info(f"Bulk upserted {len(users)} users")
            return True

        except Exception as e:
            self.logger.error(f"Error bulk upserting users: {e}")
            return False

    def save(self, user: User) -> Optional[User]:
        """
        Save a user to the database (insert if new, update if exists).

        Args:
            user (User): User to save

        Returns:
            Optional[User]: Saved user or None on error
        """
        try:
            # Check if user exists
            existing_user = self.get_user(user.id)

            if existing_user:
                # Update
                if self.update_user(user):
                    return user
            else:
                # Insert
                if self.add_user(user):
                    return user

            return None
        except Exception as e:
            self.logger.error(f"Error saving user: {e}")
            return None

    # ==================== Bank Methods ====================

    def get_bank_balance(self, user_id: int) -> Optional[int]:
        """
        Get a user's bank balance.

        Args:
            user_id (int): User ID

        Returns:
            Optional[int]: Bank balance or None on error
        """
        sql = 'SELECT bank_balance FROM Users WHERE id = %s'

        try:
            result = self.execute_query(sql, (user_id,))
            if result and len(result) > 0:
                return result[0][0]
            return None
        except Exception as e:
            self.logger.error(f"Error getting bank balance for user {user_id}: {e}")
            return None

    def update_bank_balance(self, user_id: int, new_balance: int) -> bool:
        """
        Update a user's bank balance atomically.

        Args:
            user_id (int): User ID
            new_balance (int): New bank balance

        Returns:
            bool: True if successful, False otherwise
        """
        sql = 'UPDATE Users SET bank_balance = %s WHERE id = %s'

        try:
            self.execute_query(sql, (new_balance, user_id), commit=True)
            self.logger.info(f"Updated bank balance for user {user_id} to {new_balance}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating bank balance for user {user_id}: {e}")
            return False

    def reset_daily_transfer_if_needed(self, user_id: int) -> bool:
        """
        Reset daily transfer amount if it's a new day.
        Checks last_transfer_reset and resets if different from current date.

        Args:
            user_id (int): User ID

        Returns:
            bool: True if reset occurred or not needed, False on error
        """
        from datetime import date

        sql = '''
              UPDATE Users
              SET daily_transfer_amount = 0,
                  last_transfer_reset = %s
              WHERE id = %s
                AND (last_transfer_reset IS NULL OR last_transfer_reset < %s) \
              '''

        try:
            today = date.today()
            result = self.execute_query(sql, (today, user_id, today), commit=True)
            # Check if any rows were updated
            if result is not None:
                self.logger.debug(f"Reset daily transfer for user {user_id}")
                return True
            return True  # No reset needed
        except Exception as e:
            self.logger.error(f"Error resetting daily transfer for user {user_id}: {e}")
            return False

    def increment_daily_transfer(self, user_id: int, amount: int) -> bool:
        """
        Increment the daily transfer amount for a user.
        Should be called after reset_daily_transfer_if_needed().

        Args:
            user_id (int): User ID
            amount (int): Amount to add to daily total

        Returns:
            bool: True if successful, False otherwise
        """
        sql = '''
              UPDATE Users
              SET daily_transfer_amount = daily_transfer_amount + %s
              WHERE id = %s \
              '''

        try:
            self.execute_query(sql, (amount, user_id), commit=True)
            self.logger.debug(f"Incremented daily transfer for user {user_id} by {amount}")
            return True
        except Exception as e:
            self.logger.error(f"Error incrementing daily transfer for user {user_id}: {e}")
            return False

    def add_bank_interest(self, user_id: int, interest_amount: int) -> bool:
        """
        Add interest to a user's bank balance and total currency atomically.

        Args:
            user_id (int): User ID
            interest_amount (int): The amount of interest to add

        Returns:
            bool: True if successful, False otherwise
        """
        if interest_amount <= 0:
            return True # Nothing to add

        sql = """
            UPDATE Users
            SET bank_balance = bank_balance + %s,
                total_currency = total_currency + %s,
                last_interest_payout_date = CURDATE()
            WHERE id = %s
        """
        try:
            self.execute_query(sql, (interest_amount, interest_amount, user_id), commit=True)
            self.logger.info(f"Added {interest_amount} interest to user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding bank interest for user {user_id}: {e}")
            return False