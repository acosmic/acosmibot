from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime
from database import Database
from Dao.BaseDao import BaseDao
from Entities.GuildUser import GuildUser
from Entities.BankTransaction import BankTransaction
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
                slots_free_spins_remaining INT DEFAULT 0,
                slots_locked_bet_amount INT DEFAULT 0,
                slots_bonus_total_won BIGINT DEFAULT 0,
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
                INDEX idx_last_active (guild_id, last_active DESC),
                INDEX idx_active_bonus_rounds (slots_free_spins_remaining)
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
                slots_free_spins_remaining, slots_locked_bet_amount, slots_bonus_total_won,
                messages_sent, reactions_sent, joined_at, last_active,
                daily, last_daily, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            new_guild_user.slots_free_spins_remaining,
            new_guild_user.slots_locked_bet_amount,
            new_guild_user.slots_bonus_total_won,
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
                exp_lost = %s, currency = %s,
                slots_free_spins_remaining = %s, slots_locked_bet_amount = %s, slots_bonus_total_won = %s,
                messages_sent = %s, reactions_sent = %s,
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
            updated_guild_user.slots_free_spins_remaining,
            updated_guild_user.slots_locked_bet_amount,
            updated_guild_user.slots_bonus_total_won,
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
                    slots_free_spins_remaining=user_data[11],
                    slots_locked_bet_amount=user_data[12],
                    slots_bonus_total_won=user_data[13],
                    messages_sent=user_data[14],
                    reactions_sent=user_data[15],
                    joined_at=user_data[16],
                    last_active=user_data[17],
                    daily=user_data[18],
                    last_daily=user_data[19],
                    is_active=bool(user_data[20])
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

    def get_top_guild_users(self, guild_id: int, column: str, limit: int = 10) -> List[Tuple]:
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
            SELECT user_id, name, nickname, {column}
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

    def get_top_users_by_guild_level(self, guild_id: int, limit: int = 5) -> List[Tuple]:
        sql = '''
              SELECT user_id, nickname, name, level, exp
              FROM GuildUsers
              WHERE guild_id = %s AND is_active = TRUE
              ORDER BY level DESC, exp DESC
                  LIMIT %s
              '''

        try:
            return self.execute_query(sql, (guild_id, limit)) or []
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
                        slots_free_spins_remaining=user_data[11],
                        slots_locked_bet_amount=user_data[12],
                        slots_bonus_total_won=user_data[13],
                        messages_sent=user_data[14],
                        reactions_sent=user_data[15],
                        joined_at=user_data[16],
                        last_active=user_data[17],
                        daily=user_data[18],
                        last_daily=user_data[19],
                        is_active=bool(user_data[20])
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
                        slots_free_spins_remaining=user_data[11],
                        slots_locked_bet_amount=user_data[12],
                        slots_bonus_total_won=user_data[13],
                        messages_sent=user_data[14],
                        reactions_sent=user_data[15],
                        joined_at=user_data[16],
                        last_active=user_data[17],
                        daily=user_data[18],
                        last_daily=user_data[19],
                        is_active=bool(user_data[20])
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
                # existing_guild_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                slots_free_spins_remaining=0,
                slots_locked_bet_amount=0,
                slots_bonus_total_won=0,
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

    def get_user_total_exp_across_guilds(self, user_id: int) -> int:
        """
        Get the total experience points for a user across all guilds.

        Args:
            user_id (int): User ID

        Returns:
            int: Total experience points across all guilds
        """
        sql = """
              SELECT COALESCE(SUM(exp), 0) as total_exp
              FROM GuildUsers
              WHERE user_id = %s \
                AND is_active = TRUE \
              """

        try:
            result = self.execute_query(sql, (user_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting user total exp across guilds: {e}")
            return 0

    def bulk_upsert_guild_users(self, guild_users: List[GuildUser]) -> bool:
        """
        Bulk insert or update guild users in a single transaction.
        Uses INSERT ... ON DUPLICATE KEY UPDATE for efficiency.

        Args:
            guild_users (List[GuildUser]): List of guild users to upsert

        Returns:
            bool: True if successful, False otherwise
        """
        if not guild_users:
            return True

        sql = """
            INSERT INTO GuildUsers (
                user_id, guild_id, name, nickname, level,
                streak, highest_streak, exp, exp_gained, exp_lost, currency,
                slots_free_spins_remaining, slots_locked_bet_amount, slots_bonus_total_won,
                messages_sent, reactions_sent, joined_at, last_active,
                daily, last_daily, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                nickname = VALUES(nickname),
                is_active = VALUES(is_active),
                last_active = VALUES(last_active)
        """

        try:
            # Prepare all values at once
            values_list = [
                (
                    gu.user_id,
                    gu.guild_id,
                    gu.name,
                    gu.nickname,
                    gu.level,
                    gu.streak,
                    gu.highest_streak,
                    gu.exp,
                    gu.exp_gained,
                    gu.exp_lost,
                    gu.currency,
                    gu.slots_free_spins_remaining,
                    gu.slots_locked_bet_amount,
                    gu.slots_bonus_total_won,
                    gu.messages_sent,
                    gu.reactions_sent,
                    gu.joined_at,
                    gu.last_active,
                    gu.daily,
                    gu.last_daily,
                    gu.is_active
                )
                for gu in guild_users
            ]

            # Execute with executemany for bulk insert
            self.execute_many(sql, values_list, commit=True)
            self.logger.info(f"Bulk upserted {len(guild_users)} guild users")
            return True

        except Exception as e:
            self.logger.error(f"Error bulk upserting guild users: {e}")
            return False

    def update_currency_with_global_sync(self, user_id: int, guild_id: int, currency_delta: int) -> bool:
        """
        Update guild user currency and synchronize with global user stats.
        This method ensures that both guild-specific and global currency totals are updated atomically.

        Args:
            user_id (int): Discord user ID
            guild_id (int): Discord guild ID
            currency_delta (int): Amount to change currency by (positive for gain, negative for loss)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update guild user currency
            guild_sql = """
                UPDATE GuildUsers
                SET currency = currency + %s
                WHERE user_id = %s AND guild_id = %s
            """

            # Update global user currency
            global_sql = """
                UPDATE Users
                SET total_currency = total_currency + %s,
                    last_seen = NOW()
                WHERE id = %s
            """

            # Execute both updates
            self.execute_query(guild_sql, (currency_delta, user_id, guild_id), commit=True)
            self.execute_query(global_sql, (currency_delta, user_id), commit=True)

            self.logger.debug(f"Updated currency for user {user_id} in guild {guild_id}: delta={currency_delta}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating currency with global sync for user {user_id} in guild {guild_id}: {e}")
            return False

    def update_slots_bonus_state(self, user_id: int, guild_id: int,
                                 free_spins_remaining: int,
                                 locked_bet_amount: int = 0,
                                 bonus_total_won: int = 0) -> bool:
        """
        Update user's slots bonus round state atomically.

        Args:
            user_id (int): Discord user ID
            guild_id (int): Discord guild ID
            free_spins_remaining (int): Number of free spins left (0 to end bonus)
            locked_bet_amount (int): Locked bet amount (0 to clear)
            bonus_total_won (int): Total won during bonus (0 to reset)

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            UPDATE GuildUsers
            SET slots_free_spins_remaining = %s,
                slots_locked_bet_amount = %s,
                slots_bonus_total_won = %s
            WHERE user_id = %s AND guild_id = %s
        """

        try:
            self.execute_query(sql,
                              (free_spins_remaining, locked_bet_amount, bonus_total_won,
                               user_id, guild_id),
                              commit=True)
            self.logger.debug(f"Updated slots bonus state for user {user_id} in guild {guild_id}: spins={free_spins_remaining}, bet={locked_bet_amount}, total={bonus_total_won}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating slots bonus state for user {user_id} in guild {guild_id}: {e}")
            return False

    def clear_slots_bonus_state(self, user_id: int, guild_id: int) -> bool:
        """
        Clear user's slots bonus round state (convenience method).

        Args:
            user_id (int): Discord user ID
            guild_id (int): Discord guild ID

        Returns:
            bool: True if successful, False otherwise
        """
        return self.update_slots_bonus_state(user_id, guild_id, 0, 0, 0)

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

    # ==================== Bank Transfer Methods ====================

    def transfer_to_bank(self, user_id: int, guild_id: int, amount: int, fee: int = 0) -> Dict[str, Any]:
        """
        Transfer currency from guild wallet to global bank atomically.
        Handles: guild currency deduction, bank balance increase, fee to guild vault, transaction logging.

        Args:
            user_id (int): Discord user ID
            guild_id (int): Discord guild ID
            amount (int): Amount to deposit (before fees)
            fee (int): Fee amount that goes to guild vault (default 0)

        Returns:
            Dict with keys: success (bool), message (str), balance_before (int), balance_after (int)
        """
        from Dao.UserDao import UserDao
        from Dao.BankTransactionDao import BankTransactionDao
        from Dao.GuildDao import GuildDao

        # Get a connection for the atomic transaction
        connection = None
        cursor = None

        try:
            # Validate inputs first
            with UserDao() as user_dao:
                guild_user = self.get_guild_user(user_id, guild_id)
                if not guild_user:
                    return {'success': False, 'message': 'Guild user not found'}

                user = user_dao.get_user(user_id)
                if not user:
                    return {'success': False, 'message': 'User not found'}

                # Validate sufficient funds
                if guild_user.currency < amount:
                    return {
                        'success': False,
                        'message': f'Insufficient funds. You have {guild_user.currency:,} credits in this server.'
                    }

                # Calculate net deposit (after fee)
                net_deposit = amount - fee
                balance_before = user.bank_balance
                balance_after = balance_before + net_deposit

            # Start atomic transaction with dedicated connection
            connection = self.db._get_pooled_connection(retries=3, retry_delay=0.05)
            if not connection:
                return {'success': False, 'message': 'Failed to get database connection'}

            cursor = connection.cursor()

            # 1. Deduct from guild wallet
            guild_sql = """
                UPDATE GuildUsers
                SET currency = currency - %s
                WHERE user_id = %s AND guild_id = %s
            """
            cursor.execute(guild_sql, (amount, user_id, guild_id))

            # 2. Add to bank balance
            bank_sql = """
                UPDATE Users
                SET bank_balance = bank_balance + %s
                WHERE id = %s
            """
            cursor.execute(bank_sql, (net_deposit, user_id))

            # 3. If fee exists, add to guild vault
            if fee > 0:
                vault_sql = """
                    UPDATE Guilds
                    SET vault_currency = vault_currency + %s
                    WHERE id = %s
                """
                cursor.execute(vault_sql, (fee, guild_id))

            # 4. Log transaction
            new_transaction = BankTransaction(
                user_id=user_id,
                guild_id=guild_id,
                transaction_type="deposit",
                amount=amount,
                fee=fee,
                balance_before=balance_before,
                balance_after=balance_after,
                timestamp=datetime.now())

            with BankTransactionDao() as bank_dao:
                bank_dao.add_transaction(new_transaction)

            # Commit all changes atomically
            connection.commit()

            self.logger.info(
                f"User {user_id} deposited {amount:,} (fee: {fee:,}, net: {net_deposit:,}) "
                f"to bank from guild {guild_id}. New balance: {balance_after:,}"
            )

            return {
                'success': True,
                'message': 'Deposit successful',
                'balance_before': balance_before,
                'balance_after': balance_after,
                'amount': amount,
                'fee': fee,
                'net_deposit': net_deposit
            }

        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            self.logger.error(f"Error transferring to bank for user {user_id} in guild {guild_id}: {e}")
            return {'success': False, 'message': f'Transaction failed: {str(e)}'}

        finally:
            # Clean up cursor and connection
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if connection:
                try:
                    connection.close()  # Returns to pool
                except:
                    pass

    def transfer_from_bank(self, user_id: int, guild_id: int, amount: int, fee: int = 0) -> Dict[str, Any]:
        """
        Transfer currency from global bank to guild wallet atomically.
        Handles: bank balance deduction, guild currency increase, fee to guild vault, transaction logging.

        Args:
            user_id (int): Discord user ID
            guild_id (int): Discord guild ID
            amount (int): Amount to withdraw (before fees)
            fee (int): Fee amount that goes to guild vault (default 0)

        Returns:
            Dict with keys: success (bool), message (str), balance_before (int), balance_after (int)
        """
        from Dao.UserDao import UserDao
        from Dao.BankTransactionDao import BankTransactionDao
        from Dao.GuildDao import GuildDao

        # Get a connection for the atomic transaction
        connection = None
        cursor = None

        try:
            # Validate inputs first
            with UserDao() as user_dao:
                user = user_dao.get_user(user_id)
                if not user:
                    return {'success': False, 'message': 'User not found'}

                guild_user = self.get_guild_user(user_id, guild_id)
                if not guild_user:
                    return {'success': False, 'message': 'Guild user not found'}

                # Validate sufficient bank funds (need to cover amount + fee from bank)
                total_needed = amount + fee
                if user.bank_balance < total_needed:
                    return {
                        'success': False,
                        'message': f'Insufficient bank balance. You need {total_needed:,} credits but have {user.bank_balance:,}.'
                    }

                # Calculate amounts
                balance_before = user.bank_balance
                balance_after = balance_before - total_needed

            # Start atomic transaction with dedicated connection
            connection = self.db._get_pooled_connection(retries=3, retry_delay=0.05)
            if not connection:
                return {'success': False, 'message': 'Failed to get database connection'}

            cursor = connection.cursor()

            # 1. Deduct from bank (amount + fee)
            bank_sql = """
                UPDATE Users
                SET bank_balance = bank_balance - %s
                WHERE id = %s
            """
            cursor.execute(bank_sql, (total_needed, user_id))

            # 2. Add amount to guild wallet
            guild_sql = """
                UPDATE GuildUsers
                SET currency = currency + %s
                WHERE user_id = %s AND guild_id = %s
            """
            cursor.execute(guild_sql, (amount, user_id, guild_id))

            # 3. If fee exists, add to guild vault
            if fee > 0:
                vault_sql = """
                    UPDATE Guilds
                    SET vault_currency = vault_currency + %s
                    WHERE id = %s
                """
                cursor.execute(vault_sql, (fee, guild_id))

            # 4. Log transaction
            new_transaction = BankTransaction(
                user_id=user_id,
                guild_id=guild_id,
                transaction_type="withdraw",
                amount=amount,
                fee=fee,
                balance_before=balance_before,
                balance_after=balance_after,
                timestamp=datetime.now())

            with BankTransactionDao() as bank_dao:
                bank_dao.add_transaction(new_transaction)

            # Commit all changes atomically
            connection.commit()

            self.logger.info(
                f"User {user_id} withdrew {amount:,} (fee: {fee:,}) "
                f"from bank to guild {guild_id}. New balance: {balance_after:,}"
            )

            return {
                'success': True,
                'message': 'Withdrawal successful',
                'balance_before': balance_before,
                'balance_after': balance_after,
                'amount': amount,
                'fee': fee
            }

        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            self.logger.error(f"Error transferring from bank for user {user_id} in guild {guild_id}: {e}")
            return {'success': False, 'message': f'Transaction failed: {str(e)}'}

        finally:
            # Clean up cursor and connection
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if connection:
                try:
                    connection.close()  # Returns to pool
                except:
                    pass