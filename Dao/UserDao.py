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
                               total_exp INT DEFAULT 0,
                               total_currency INT DEFAULT 0,
                               total_messages INT DEFAULT 0,
                               total_reactions INT DEFAULT 0,
                               account_created DATETIME,
                               first_seen DATETIME,
                               last_seen DATETIME,
                               privacy_settings JSON,
                               global_settings JSON
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
                                 total_exp, \
                                 total_currency, \
                                 total_messages, \
                                 total_reactions, \
                                 account_created, \
                                 first_seen, \
                                 last_seen, \
                                 privacy_settings, \
                                 global_settings) \
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) \
              '''
        values = (
            new_user.id,
            new_user.discord_username,
            new_user.global_name,
            new_user.avatar_url,
            new_user.is_bot,
            new_user.total_exp,
            new_user.total_currency,
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
                  total_exp        = %s,
                  total_currency   = %s,
                  total_messages   = %s,
                  total_reactions  = %s,
                  account_created  = %s,
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
            updated_user.total_exp,
            updated_user.total_currency,
            updated_user.total_messages,
            updated_user.total_reactions,
            updated_user.account_created,
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
        """
        Get a user by their ID.

        Args:
            id (int): User ID

        Returns:
            Optional[User]: User if found, None otherwise
        """
        sql = 'SELECT * FROM Users WHERE id = %s'

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
                    total_exp=user_data[5],
                    total_currency=user_data[6],
                    total_messages=user_data[7],
                    total_reactions=user_data[8],
                    account_created=user_data[9],
                    first_seen=user_data[10],
                    last_seen=user_data[11],
                    privacy_settings=user_data[12],
                    global_settings=user_data[13]
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
        sql = 'SELECT * FROM Users WHERE discord_username = %s'

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
                    total_exp=user_data[5],
                    total_currency=user_data[6],
                    total_messages=user_data[7],
                    total_reactions=user_data[8],
                    account_created=user_data[9],
                    first_seen=user_data[10],
                    last_seen=user_data[11],
                    privacy_settings=user_data[12],
                    global_settings=user_data[13]
                )
                return user
            return None

        except Exception as e:
            self.logger.error(f"Error getting user by username: {e}")
            return None

    def get_user_rank_by_exp(self, id: int) -> Optional[Tuple]:
        """
        Get a user's rank based on total experience points.

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
                            total_exp, \
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
                             WHERE u2.total_exp > u1.total_exp AND u2.is_bot = FALSE) AS user_rank
                     FROM Users u1
                     WHERE id = %s; \
                     '''

        try:
            result = self.execute_query(rank_query, (id,))
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Error getting user rank by exp: {e}")
            return None

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
                            total_exp, \
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

    def get_top_users_by_exp(self, limit: int = 5) -> List[Tuple]:
        """
        Get the top users by total experience.

        Args:
            limit (int, optional): Maximum number of users to return. Defaults to 5.

        Returns:
            List[Tuple]: List of top users
        """
        sql = '''
              SELECT id, discord_username, global_name, total_exp
              FROM Users
              WHERE is_bot = FALSE
              ORDER BY total_exp DESC
                  LIMIT %s \
              '''

        try:
            return self.execute_query(sql, (limit,)) or []
        except Exception as e:
            self.logger.error(f"Error getting top users by exp: {e}")
            return []

    def get_top_users_by_currency(self, limit: int = 5) -> List[Tuple]:
        """
        Get the top users by total currency.

        Args:
            limit (int, optional): Maximum number of users to return. Defaults to 5.

        Returns:
            List[Tuple]: List of top users
        """
        sql = '''
              SELECT id, discord_username, global_name, total_currency
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

    def get_total_exp(self) -> int:
        """
        Get the total amount of experience points earned by all users.

        Returns:
            int: Total experience points
        """
        sql = 'SELECT SUM(total_exp) FROM Users WHERE is_bot = FALSE'

        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total experience: {e}")
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
              SELECT * \
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
                        total_exp=user_data[5],
                        total_currency=user_data[6],
                        total_messages=user_data[7],
                        total_reactions=user_data[8],
                        account_created=user_data[9],
                        first_seen=user_data[10],
                        last_seen=user_data[11],
                        privacy_settings=user_data[12],
                        global_settings=user_data[13]
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

    def increment_user_stats(self, user_id: int, exp_gain: int = 0, currency_gain: int = 0,
                             messages_gain: int = 0, reactions_gain: int = 0) -> bool:
        """
        Increment user statistics.

        Args:
            user_id (int): User ID
            exp_gain (int, optional): Experience to add. Defaults to 0.
            currency_gain (int, optional): Currency to add. Defaults to 0.
            messages_gain (int, optional): Messages to add. Defaults to 0.
            reactions_gain (int, optional): Reactions to add. Defaults to 0.

        Returns:
            bool: True if successful, False otherwise
        """
        sql = '''
              UPDATE Users
              SET total_exp       = total_exp + %s,
                  total_currency  = total_currency + %s,
                  total_messages  = total_messages + %s,
                  total_reactions = total_reactions + %s,
                  last_seen       = NOW()
              WHERE id = %s \
              '''

        try:
            self.execute_query(sql, (exp_gain, currency_gain, messages_gain, reactions_gain, user_id), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error incrementing user stats: {e}")
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