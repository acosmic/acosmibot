from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime
from database import Database
from Dao.BaseDao import BaseDao
from Entities.Guild import Guild
from dotenv import load_dotenv
import os
import logging


class GuildDao(BaseDao[Guild]):
    """
    Data Access Object for Guild entities.
    Provides methods to interact with the Guilds table in the database.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the GuildDao with connection parameters.

        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(Guild, "Guilds", db)

    def create_table(self) -> bool:
        """
        Create the Guilds table if it doesn't exist.

        Returns:
            bool: True if successful, False otherwise
        """
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS Guilds (
                id BIGINT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                owner_id BIGINT NOT NULL,
                member_count INT DEFAULT 0,
                active BOOLEAN DEFAULT TRUE,
                settings JSON,
                created DATETIME,
                last_active DATETIME
            )
        """

        try:
            self.create_table_if_not_exists(create_table_sql)
            return True
        except Exception as e:
            self.logger.error(f"Error creating Guilds table: {e}")
            return False

    def add_new_guild(self, guild: Guild) -> bool:
        """
        Add a new guild to the database.

        Args:
            guild (Guild): Guild to add

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            INSERT INTO Guilds (id, name, owner_id, member_count, active, settings, created, last_active) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            guild.id,
            guild.name,
            guild.owner_id,
            guild.member_count,
            guild.active,
            guild.settings,
            guild.created,
            guild.last_active
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding guild: {e}")
            return False

    def get_guild(self, guild_id: int) -> Optional[Guild]:
        """
        Get a guild by its ID.

        Args:
            guild_id (int): Discord guild ID

        Returns:
            Optional[Guild]: Guild if found, None otherwise
        """
        sql = """
            SELECT id, name, owner_id, member_count, active, settings, created, last_active
            FROM Guilds
            WHERE id = %s
        """

        try:
            result = self.execute_query(sql, (guild_id,))

            if result and len(result) > 0:
                guild_data = result[0]
                return Guild(
                    guild_data[0], guild_data[1], guild_data[2],
                    guild_data[3], guild_data[4], guild_data[5],
                    guild_data[6], guild_data[7]
                )
            return None

        except Exception as e:
            self.logger.error(f"Error getting guild: {e}")
            return None

    def update_guild(self, guild: Guild) -> bool:
        """
        Update an existing guild.

        Args:
            guild (Guild): Guild to update

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            UPDATE Guilds
            SET name = %s, owner_id = %s, member_count = %s, active = %s, 
                settings = %s, last_active = %s
            WHERE id = %s
        """
        values = (
            guild.name,
            guild.owner_id,
            guild.member_count,
            guild.active,
            guild.settings,
            guild.last_active,
            guild.id
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating guild: {e}")
            return False

    def get_all_guilds(self) -> List[Guild]:
        """
        Get all guilds from the database.

        Returns:
            List[Guild]: List of all guilds
        """
        sql = """
            SELECT id, name, owner_id, member_count, active, settings, created, last_active
            FROM Guilds
        """

        try:
            results = self.execute_query(sql)

            guilds = []
            if results:
                for guild_data in results:
                    guilds.append(Guild(
                        guild_data[0], guild_data[1], guild_data[2],
                        guild_data[3], guild_data[4], guild_data[5],
                        guild_data[6], guild_data[7]
                    ))

            return guilds

        except Exception as e:
            self.logger.error(f"Error getting all guilds: {e}")
            return []

    def delete_guild(self, guild_id: int) -> bool:
        """
        Delete a guild by its ID.

        Args:
            guild_id (int): Discord guild ID

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            DELETE FROM Guilds
            WHERE id = %s
        """

        try:
            self.execute_query(sql, (guild_id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting guild: {e}")
            return False

    def save(self, guild: Guild) -> Optional[Guild]:
        """
        Save a guild to the database (insert if new, update if exists).

        Args:
            guild (Guild): Guild to save

        Returns:
            Optional[Guild]: Saved guild or None on error
        """
        try:
            # Check if guild exists
            existing_guild = self.get_guild(guild.id)

            if existing_guild:
                # Update
                if self.update_guild(guild):
                    return guild
            else:
                # Insert
                if self.add_new_guild(guild):
                    return guild

            return None
        except Exception as e:
            self.logger.error(f"Error saving guild: {e}")
            return None