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
        CREATE TABLE IF NOT EXISTS Users (
            id BIGINT PRIMARY KEY,
            discord_username VARCHAR(255) NOT NULL,
            nickname VARCHAR(255),
            level INT DEFAULT 0,
            season_level INT DEFAULT 0,
            season_exp INT DEFAULT 0,
            streak INT DEFAULT 0,
            highest_streak INT DEFAULT 0,
            exp INT DEFAULT 0,
            exp_gained INT DEFAULT 0,
            exp_lost INT DEFAULT 0,
            currency INT DEFAULT 0,
            messages_sent INT DEFAULT 0,
            reactions_sent INT DEFAULT 0,
            created DATETIME,
            last_active DATETIME,
            daily INT DEFAULT 0,
            last_daily DATETIME NULL
        )
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
        INSERT INTO Users (
            id,
            discord_username,
            nickname,
            level,
            season_level,
            season_exp,
            streak,
            highest_streak,
            exp,
            exp_gained,
            exp_lost,
            currency,
            messages_sent,
            reactions_sent,
            created,
            last_active,
            daily,
            last_daily
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        values = (
            new_user.id,
            new_user.discord_username,
            new_user.nickname,
            new_user.level,
            new_user.season_level,
            new_user.season_exp,
            new_user.streak,
            new_user.highest_streak,
            new_user.exp,
            new_user.exp_gained,
            new_user.exp_lost,
            new_user.currency,
            new_user.messages_sent,
            new_user.reactions_sent,
            new_user.created,
            new_user.last_active,
            new_user.daily,
            new_user.last_daily
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
            SET
                discord_username = %s,
                nickname = %s,
                level = %s,
                season_level = %s,
                season_exp = %s,
                streak = %s,
                highest_streak = %s,
                exp = %s,
                exp_gained = %s,
                exp_lost = %s,
                currency = %s,
                messages_sent = %s,
                reactions_sent = %s,
                last_active = %s,
                daily = %s,
                last_daily = %s
            WHERE id = %s
        '''
        values = (
            updated_user.discord_username,
            updated_user.nickname,
            updated_user.level,
            updated_user.season_level,
            updated_user.season_exp,
            updated_user.streak,
            updated_user.highest_streak,
            updated_user.exp,
            updated_user.exp_gained,
            updated_user.exp_lost,
            updated_user.currency,
            updated_user.messages_sent,
            updated_user.reactions_sent,
            updated_user.last_active,
            updated_user.daily,
            updated_user.last_daily,
            updated_user.id,
        )
        
        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating user: {e}")
            return False

    def reset_daily(self) -> bool:
        """
        Reset the daily status for all users.
        
        Returns:
            bool: True if successful, False otherwise
        """
        sql = 'UPDATE Users SET daily = 0'
        
        try:
            self.execute_query(sql, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error resetting daily status: {e}")
            return False

    def reset_streak(self, id: int) -> bool:
        """
        Reset the streak for a specific user.
        
        Args:
            id (int): User ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = 'UPDATE Users SET streak = 0 WHERE id = %s'
        
        try:
            self.execute_query(sql, (id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error resetting streak: {e}")
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
                    nickname=user_data[2],
                    level=user_data[3],
                    season_level=user_data[4],
                    season_exp=user_data[5],
                    streak=user_data[6],
                    highest_streak=user_data[7],
                    exp=user_data[8],
                    exp_gained=user_data[9],
                    exp_lost=user_data[10],
                    currency=user_data[11],
                    messages_sent=user_data[12],
                    reactions_sent=user_data[13],
                    created=user_data[14],
                    last_active=user_data[15],
                    daily=user_data[16],
                    last_daily=user_data[17]
                )
                return user
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_rank(self, id: int) -> Optional[Tuple]:
        """
        Get a user's rank based on experience points.
        
        Args:
            id (int): User ID
            
        Returns:
            Optional[Tuple]: User data with rank if found, None otherwise
        """
        rank_query = '''
            SELECT
                id,
                discord_username,
                nickname,
                level,
                season_level,
                season_exp,
                streak,
                highest_streak,
                exp,
                exp_gained,
                exp_lost,
                currency,
                messages_sent,
                reactions_sent,
                created,
                last_active,
                daily,
                last_daily,
                (SELECT COUNT(*) + 1 FROM Users u2 WHERE u2.exp > u1.exp) AS user_rank
            FROM Users u1
            WHERE id = %s;
        '''
        
        try:
            result = self.execute_query(rank_query, (id,))
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Error getting user rank: {e}")
            return None
    
    def get_top_users(self, column: str, limit: int = 5) -> List[Tuple]:
        """
        Get the top users by a specific column.
        
        Args:
            column (str): Column to sort by
            limit (int, optional): Maximum number of users to return. Defaults to 5.
            
        Returns:
            List[Tuple]: List of top users
        """
        sql = f'''
        SELECT id, discord_username, {column}
        FROM Users
        ORDER BY {column} DESC
        LIMIT {limit}
        '''
        
        try:
            return self.execute_query(sql) or []
        except Exception as e:
            self.logger.error(f"Error getting top users: {e}")
            return []
    
    def get_total_messages(self) -> int:
        """
        Get the total number of messages sent by all users.
        
        Returns:
            int: Total number of messages
        """
        sql = 'SELECT SUM(messages_sent) FROM Users'
        
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
        sql = 'SELECT SUM(reactions_sent) FROM Users'
        
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
        sql = 'SELECT SUM(currency) FROM Users'
        
        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total currency: {e}")
            return 0
    
    def get_total_users(self) -> int:
        """
        Get the total number of users.
        
        Returns:
            int: Total number of users
        """
        sql = 'SELECT COUNT(*) FROM Users'
        
        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total users: {e}")
            return 0
    
    def get_total_active_users(self) -> int:
        """
        Get the total number of active users in the last 24 hours.
        
        Returns:
            int: Total number of active users
        """
        sql = '''
        SELECT COUNT(*)
        FROM Users
        WHERE last_active > DATE_SUB(NOW(), INTERVAL 1 DAY)
        '''
        
        try:
            result = self.execute_query(sql)
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
        sql = 'SELECT SUM(exp) FROM Users'
        
        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total experience: {e}")
            return 0
    
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