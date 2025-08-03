from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime
from database import Database
from Dao.BaseDao import BaseDao
from Entities.GuildUser import GuildUser
from dotenv import load_dotenv
import os
import logging


class GuildUserDao(BaseDao[GuildUser]):
    """
    Data Access Object for GuildUser entities.
    Provides methods to interact with the GuildUsers table in the database.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the GuildUserDao with connection parameters.

        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(GuildUser, "GuildUsers", db)

    def create_table(self) -> bool:
        """
        Create the GuildUsers table if it doesn't exist.

        Returns:
            bool: True if successful, False otherwise
        """
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS GuildUsers (
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                name VARCHAR(255) NOT NULL,
                nickname VARCHAR(255),
                level INT DEFAULT 0,
                streak INT DEFAULT 0,
                highest_streak INT DEFAULT 0,
                exp INT DEFAULT 0,
                exp_gained INT DEFAULT 0,
                exp_lost INT DEFAULT 0,
                currency INT DEFAULT 0,
                messages_sent INT DEFAULT 0,
                reactions_sent INT DEFAULT 0,
                joined_at DATETIME,
                last_active DATETIME,
                daily INT DEFAULT 0,
                last_daily DATETIME NULL,
                is_active BOOLEAN DEFAULT TRUE,
                PRIMARY KEY (user_id, guild_id),
                INDEX idx_guild_exp (guild_id, exp DESC),
                INDEX idx_guild_currency (guild_id, currency DESC),
                INDEX idx_guild_level (guild_id, level DESC),
                INDEX idx_last_active (guild_id, last_active DESC)
            )
        """

        try:
            self.create_table_if_not_exists(create_table_sql)
            return True
        except Exception as e:
            self.logger.error(f"Error creating GuildUsers table: {e}")
            return False

    def add_guild_user(self, new_guild_user: GuildUser) -> bool:
        """
        Add a new guild user to the database.

        Args:
            new_guild_user (GuildUser): Guild user to add

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            INSERT INTO GuildUsers (
                user_id, guild_id, name, nickname, level,
                streak, highest_streak, exp, exp_gained, exp_lost, currency,
                messages_sent, reactions_sent, joined_at, last_active,
                daily, last_daily, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            new_guild_user.user_id,
            new_guild_user.guild_id,
            new_guild_user.name,
            new_guild_user.nickname,
            new_guild_user.level,
            new_guild_user.streak,
            new_guild_user.highest_streak,
            new_guild_user.exp,
            new_guild_user.exp_gained,
            new_guild_user.exp_lost,
            new_guild_user.currency,
            new_guild_user.messages_sent,
            new_guild_user.reactions_sent,
            new_guild_user.joined_at,
            new_guild_user.last_active,
            new_guild_user.daily,
            new_guild_user.last_daily,
            new_guild_user.is_active
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding guild user: {e}")
            return False

    def update_guild_user(self, updated_guild_user: GuildUser) -> bool:
        """
        Update an existing guild user in the database.

        Args:
            updated_guild_user (GuildUser): Guild user to update

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            UPDATE GuildUsers
            SET name = %s, nickname = %s, level = %s,
                streak = %s, highest_streak = %s, exp = %s, exp_gained = %s,
                exp_lost = %s, currency = %s, messages_sent = %s, reactions_sent = %s,
                last_active = %s, daily = %s, last_daily = %s, is_active = %s
            WHERE user_id = %s AND guild_id = %s
        """
        values = (
            updated_guild_user.name,
            updated_guild_user.nickname,
            updated_guild_user.level,
            updated_guild_user.streak,
            updated_guild_user.highest_streak,
            updated_guild_user.exp,
            updated_guild_user.exp_gained,
            updated_guild_user.exp_lost,
            updated_guild_user.currency,
            updated_guild_user.messages_sent,
            updated_guild_user.reactions_sent,
            updated_guild_user.last_active,
            updated_guild_user.daily,
            updated_guild_user.last_daily,
            updated_guild_user.is_active,
            updated_guild_user.user_id,
            updated_guild_user.guild_id,
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating guild user: {e}")
            return False

    def reset_daily(self, guild_id: int) -> bool:
        """
        Reset the daily status for all users in a guild.

        Args:
            guild_id (int): Guild ID

        Returns:
            bool: True if successful, False otherwise
        """
        sql = 'UPDATE GuildUsers SET daily = 0 WHERE guild_id = %s'

        try:
            self.execute_query(sql, (guild_id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error resetting daily status: {e}")
            return False

    def reset_streak(self, user_id: int, guild_id: int) -> bool:
        """
        Reset the streak for a specific user in a guild.

        Args:
            user_id (int): User ID
            guild_id (int): Guild ID

        Returns:
            bool: True if successful, False otherwise
        """
        sql = 'UPDATE GuildUsers SET streak = 0 WHERE user_id = %s AND guild_id = %s'

        try:
            self.execute_query(sql, (user_id, guild_id), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error resetting streak: {e}")
            return False

    def get_guild_user(self, user_id: int, guild_id: int) -> Optional[GuildUser]:
        """
        Get a guild user by their user ID and guild ID.

        Args:
            user_id (int): User ID
            guild_id (int): Guild ID

        Returns:
            Optional[GuildUser]: Guild user if found, None otherwise
        """
        sql = 'SELECT * FROM GuildUsers WHERE user_id = %s AND guild_id = %s'

        try:
            result = self.execute_query(sql, (user_id, guild_id))

            if result and len(result) > 0:
                user_data = result[0]
                guild_user = GuildUser(
                    user_id=user_data[0],
                    guild_id=user_data[1],
                    name=user_data[2],
                    nickname=user_data[3],
                    level=user_data[4],
                    streak=user_data[5],
                    highest_streak=user_data[6],
                    exp=user_data[7],
                    exp_gained=user_data[8],
                    exp_lost=user_data[9],
                    currency=user_data[10],
                    messages_sent=user_data[11],
                    reactions_sent=user_data[12],
                    joined_at=user_data[13],
                    last_active=user_data[14],
                    daily=user_data[15],
                    last_daily=user_data[16],
                    is_active=bool(user_data[17])
                )
                return guild_user
            return None

        except Exception as e:
            self.logger.error(f"Error getting guild user: {e}")
            return None

    def get_guild_user_rank(self, user_id: int, guild_id: int) -> Optional[Tuple]:
        """
        Get a guild user's rank based on experience points within their guild.

        Args:
            user_id (int): User ID
            guild_id (int): Guild ID

        Returns:
            Optional[Tuple]: User data with rank if found, None otherwise
        """
        rank_query = """
            SELECT name, user_id, guild_id, nickname, level,
                   streak, highest_streak, exp, exp_gained, exp_lost, currency,
                   messages_sent, reactions_sent, joined_at, last_active,
                   daily, last_daily, is_active,
                   (SELECT COUNT(*) + 1 
                    FROM GuildUsers gu2 
                    WHERE gu2.exp > gu1.exp 
                      AND gu2.guild_id = gu1.guild_id 
                      AND gu2.is_active = TRUE) AS user_rank
            FROM GuildUsers gu1
            WHERE user_id = %s AND guild_id = %s
        """

        try:
            result = self.execute_query(rank_query, (user_id, guild_id))
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Error getting guild user rank: {e}")
            return None

    def get_top_guild_users(self, guild_id: int, column: str, limit: int = 5) -> List[Tuple]:
        """
        Get the top guild users by a specific column within a guild.

        Args:
            guild_id (int): Guild ID
            column (str): Column to sort by
            limit (int, optional): Maximum number of users to return. Defaults to 5.

        Returns:
            List[Tuple]: List of top guild users
        """
        sql = f"""
            SELECT user_id, nickname, {column}
            FROM GuildUsers
            WHERE guild_id = %s AND is_active = TRUE
            ORDER BY {column} DESC
            LIMIT {limit}
        """

        try:
            return self.execute_query(sql, (guild_id,)) or []
        except Exception as e:
            self.logger.error(f"Error getting top guild users: {e}")
            return []

    def get_guild_users(self, guild_id: int, active_only: bool = True) -> List[GuildUser]:
        """
        Get all users in a guild.

        Args:
            guild_id (int): Guild ID
            active_only (bool, optional): Only return active users. Defaults to True.

        Returns:
            List[GuildUser]: List of guild users
        """
        if active_only:
            sql = 'SELECT * FROM GuildUsers WHERE guild_id = %s AND is_active = TRUE ORDER BY exp DESC'
        else:
            sql = 'SELECT * FROM GuildUsers WHERE guild_id = %s ORDER BY exp DESC'

        try:
            results = self.execute_query(sql, (guild_id,))

            guild_users = []
            if results:
                for user_data in results:
                    guild_users.append(GuildUser(
                        user_id=user_data[0],
                        guild_id=user_data[1],
                        name=user_data[2],
                        nickname=user_data[3],
                        level=user_data[4],
                        streak=user_data[5],
                        highest_streak=user_data[6],
                        exp=user_data[7],
                        exp_gained=user_data[8],
                        exp_lost=user_data[9],
                        currency=user_data[10],
                        messages_sent=user_data[11],
                        reactions_sent=user_data[12],
                        joined_at=user_data[13],
                        last_active=user_data[14],
                        daily=user_data[15],
                        last_daily=user_data[16],
                        is_active=bool(user_data[17])
                    ))

            return guild_users

        except Exception as e:
            self.logger.error(f"Error getting guild users: {e}")
            return []

    def get_user_guilds(self, user_id: int, active_only: bool = True) -> List[GuildUser]:
        """
        Get all guilds a user is in.

        Args:
            user_id (int): User ID
            active_only (bool, optional): Only return active guild memberships. Defaults to True.

        Returns:
            List[GuildUser]: List of user's guild memberships
        """
        if active_only:
            sql = 'SELECT * FROM GuildUsers WHERE user_id = %s AND is_active = TRUE ORDER BY last_active DESC'
        else:
            sql = 'SELECT * FROM GuildUsers WHERE user_id = %s ORDER BY last_active DESC'

        try:
            results = self.execute_query(sql, (user_id,))

            guild_users = []
            if results:
                for user_data in results:
                    guild_users.append(GuildUser(
                        user_id=user_data[0],
                        guild_id=user_data[1],
                        name=user_data[2],
                        nickname=user_data[3],
                        level=user_data[4],
                        streak=user_data[5],
                        highest_streak=user_data[6],
                        exp=user_data[7],
                        exp_gained=user_data[8],
                        exp_lost=user_data[9],
                        currency=user_data[10],
                        messages_sent=user_data[11],
                        reactions_sent=user_data[12],
                        joined_at=user_data[13],
                        last_active=user_data[14],
                        daily=user_data[15],
                        last_daily=user_data[16],
                        is_active=bool(user_data[17])
                    ))

            return guild_users

        except Exception as e:
            self.logger.error(f"Error getting user guilds: {e}")
            return []

    def deactivate_guild_user(self, user_id: int, guild_id: int) -> bool:
        """
        Deactivate a guild user (when they leave the guild).

        Args:
            user_id (int): User ID
            guild_id (int): Guild ID

        Returns:
            bool: True if successful, False otherwise
        """
        sql = 'UPDATE GuildUsers SET is_active = FALSE WHERE user_id = %s AND guild_id = %s'

        try:
            self.execute_query(sql, (user_id, guild_id), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error deactivating guild user: {e}")
            return False

    def activate_guild_user(self, user_id: int, guild_id: int) -> bool:
        """
        Activate a guild user (when they rejoin the guild).

        Args:
            user_id (int): User ID
            guild_id (int): Guild ID

        Returns:
            bool: True if successful, False otherwise
        """
        sql = 'UPDATE GuildUsers SET is_active = TRUE WHERE user_id = %s AND guild_id = %s'

        try:
            self.execute_query(sql, (user_id, guild_id), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error activating guild user: {e}")
            return False

    def get_guild_stats(self, guild_id: int) -> Dict[str, int]:
        """
        Get statistics for a guild.

        Args:
            guild_id (int): Guild ID

        Returns:
            Dict[str, int]: Dictionary containing various guild statistics
        """
        stats = {}

        try:
            # Total active users
            sql = 'SELECT COUNT(*) FROM GuildUsers WHERE guild_id = %s AND is_active = TRUE'
            result = self.execute_query(sql, (guild_id,))
            stats['total_active_users'] = result[0][0] if result and result[0][0] else 0

            # Total messages
            sql = 'SELECT SUM(messages_sent) FROM GuildUsers WHERE guild_id = %s AND is_active = TRUE'
            result = self.execute_query(sql, (guild_id,))
            stats['total_messages'] = result[0][0] if result and result[0][0] else 0

            # Total reactions
            sql = 'SELECT SUM(reactions_sent) FROM GuildUsers WHERE guild_id = %s AND is_active = TRUE'
            result = self.execute_query(sql, (guild_id,))
            stats['total_reactions'] = result[0][0] if result and result[0][0] else 0

            # Total currency
            sql = 'SELECT SUM(currency) FROM GuildUsers WHERE guild_id = %s AND is_active = TRUE'
            result = self.execute_query(sql, (guild_id,))
            stats['total_currency'] = result[0][0] if result and result[0][0] else 0

            # Total exp
            sql = 'SELECT SUM(exp) FROM GuildUsers WHERE guild_id = %s AND is_active = TRUE'
            result = self.execute_query(sql, (guild_id,))
            stats['total_exp'] = result[0][0] if result and result[0][0] else 0

            return stats

        except Exception as e:
            self.logger.error(f"Error getting guild stats: {e}")
            return {}

    def get_or_create_guild_user_from_discord(self, discord_member, guild_id: int) -> Optional[GuildUser]:
        """
        Get existing guild user or create new one from Discord member object.

        Args:
            discord_member: Discord member object (discord.Member)
            guild_id (int): Guild ID

        Returns:
            Optional[GuildUser]: GuildUser object or None on error
        """
        try:
            # First try to get existing guild user
            existing_guild_user = self.get_guild_user(discord_member.id, guild_id)
            if existing_guild_user:
                # Update basic info and reactivate if needed
                existing_guild_user.name = discord_member.name
                existing_guild_user.nickname = discord_member.display_name
                existing_guild_user.is_active = True
                existing_guild_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.update_guild_user(existing_guild_user)
                return existing_guild_user

            # Create new guild user
            formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Handle joined_at safely
            try:
                joined_at = discord_member.joined_at.strftime(
                    "%Y-%m-%d %H:%M:%S") if discord_member.joined_at else formatted_date
            except Exception:
                joined_at = formatted_date

            new_guild_user = GuildUser(
                user_id=discord_member.id,
                guild_id=guild_id,
                name=discord_member.name,
                nickname=discord_member.display_name,
                level=0,
                streak=0,
                highest_streak=0,
                exp=0,
                exp_gained=0,
                exp_lost=0,
                currency=1000,  # Starting currency
                messages_sent=0,
                reactions_sent=0,
                joined_at=joined_at,
                last_active=formatted_date,
                daily=0,
                last_daily=None,
                is_active=True
            )

            if self.add_guild_user(new_guild_user):
                self.logger.info(f"Created new guild user: {discord_member.name} in guild {guild_id}")
                return new_guild_user
            else:
                self.logger.error(f"Failed to create guild user: {discord_member.name} in guild {guild_id}")
                return None

        except Exception as e:
            self.logger.error(f"Error getting/creating guild user {discord_member.name} in guild {guild_id}: {e}")
            return None

    def ensure_guild_user_exists(self, discord_member, guild_id: int) -> bool:
        """
        Ensure a guild user exists in the database, create if not.

        Args:
            discord_member: Discord member object
            guild_id (int): Guild ID

        Returns:
            bool: True if guild user exists/was created, False on error
        """
        try:
            guild_user = self.get_or_create_guild_user_from_discord(discord_member, guild_id)
            return guild_user is not None
        except Exception as e:
            self.logger.error(f"Error ensuring guild user exists for {discord_member.name}: {e}")
            return False

    def reactivate_guild_user(self, user_id: int, guild_id: int) -> bool:
        """
        Reactivate a guild user (useful when they rejoin a guild).

        Args:
            user_id (int): User ID
            guild_id (int): Guild ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            guild_user = self.get_guild_user(user_id, guild_id)
            if guild_user:
                guild_user.is_active = True
                guild_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return self.update_guild_user(guild_user)
            return False
        except Exception as e:
            self.logger.error(f"Error reactivating guild user {user_id} in guild {guild_id}: {e}")
            return False

    def save(self, guild_user: GuildUser) -> Optional[GuildUser]:
        """
        Save a guild user to the database (insert if new, update if exists).

        Args:
            guild_user (GuildUser): Guild user to save

        Returns:
            Optional[GuildUser]: Saved guild user or None on error
        """
        try:
            # Check if guild user exists
            existing_guild_user = self.get_guild_user(guild_user.user_id, guild_user.guild_id)

            if existing_guild_user:
                # Update
                if self.update_guild_user(guild_user):
                    return guild_user
            else:
                # Insert
                if self.add_guild_user(guild_user):
                    return guild_user

            return None
        except Exception as e:
            self.logger.error(f"Error saving guild user: {e}")
            return None