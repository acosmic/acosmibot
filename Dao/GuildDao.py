from typing import Optional, List, Dict, Any, Tuple, Union

from Entities.GuildUser import GuildUser
from database import Database
from Dao.BaseDao import BaseDao
from Entities.Guild import Guild
from datetime import datetime
import json


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
                active TINYINT(1) DEFAULT 1,
                settings JSON,
                created DATETIME,
                last_active DATETIME,
                vault_currency BIGINT DEFAULT 0,
                ai_enabled TINYINT(1) DEFAULT 0,
                ai_thread_id VARCHAR(255) NULL,
                ai_temperature FLOAT DEFAULT 1,
                ai_personality_traits JSON
            );
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
            INSERT INTO Guilds (
                id, name, owner_id, member_count, active, settings, created, last_active,
                vault_currency, ai_enabled, ai_thread_id, ai_temperature, ai_personality_traits
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Convert personality traits dict to JSON string
        personality_json = json.dumps(guild.ai_personality_traits) if guild.ai_personality_traits else None

        values = (
            guild.id,
            guild.name,
            guild.owner_id,
            guild.member_count,
            guild.active,
            guild.settings,
            guild.created,
            guild.last_active,
            guild.vault_currency,
            guild.ai_enabled,
            guild.ai_thread_id,
            guild.ai_temperature,
            personality_json
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
            SELECT id, name, owner_id, member_count, active, settings, created, last_active,
                   vault_currency, ai_enabled, ai_thread_id, ai_temperature, ai_personality_traits
            FROM Guilds
            WHERE id = %s
        """

        try:
            result = self.execute_query(sql, (guild_id,))

            if result and len(result) > 0:
                guild_data = result[0]

                # Parse JSON personality traits
                personality_traits = None
                if guild_data[12]:  # ai_personality_traits
                    try:
                        personality_traits = json.loads(guild_data[12])
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON in ai_personality_traits for guild {guild_id}")
                        personality_traits = {"humor_level": "high", "sarcasm_level": "medium", "nerd_level": "high",
                                              "friendliness": "high"}

                return Guild(
                    id=guild_data[0],
                    name=guild_data[1],
                    owner_id=guild_data[2],
                    member_count=guild_data[3],
                    active=guild_data[4],
                    settings=guild_data[5],
                    created=guild_data[6],
                    last_active=guild_data[7],
                    vault_currency=guild_data[8],
                    ai_enabled=guild_data[9],
                    ai_thread_id=guild_data[10],
                    ai_temperature=guild_data[11],
                    ai_personality_traits=personality_traits
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
                settings = %s, last_active = %s, vault_currency = %s, 
                ai_enabled = %s, ai_thread_id = %s, ai_temperature = %s, 
                ai_personality_traits = %s
            WHERE id = %s
        """

        # Convert personality traits dict to JSON string
        personality_json = json.dumps(guild.ai_personality_traits) if guild.ai_personality_traits else None

        values = (
            guild.name,
            guild.owner_id,
            guild.member_count,
            guild.active,
            guild.settings,
            guild.last_active,
            guild.vault_currency,
            guild.ai_enabled,
            guild.ai_thread_id,
            guild.ai_temperature,
            personality_json,
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
            SELECT id, name, owner_id, member_count, active, settings, created, last_active,
                   vault_currency, ai_enabled, ai_thread_id, ai_temperature, ai_personality_traits
            FROM Guilds
        """

        try:
            results = self.execute_query(sql)

            guilds = []
            if results:
                for guild_data in results:
                    # Parse JSON personality traits
                    personality_traits = None
                    if guild_data[12]:  # ai_personality_traits
                        try:
                            personality_traits = json.loads(guild_data[12])
                        except json.JSONDecodeError:
                            self.logger.warning(f"Invalid JSON in ai_personality_traits for guild {guild_data[0]}")
                            personality_traits = {"humor_level": "high", "sarcasm_level": "medium",
                                                  "nerd_level": "high", "friendliness": "high"}

                    guilds.append(Guild(
                        id=guild_data[0],
                        name=guild_data[1],
                        owner_id=guild_data[2],
                        member_count=guild_data[3],
                        active=guild_data[4],
                        settings=guild_data[5],
                        created=guild_data[6],
                        last_active=guild_data[7],
                        vault_currency=guild_data[8],
                        ai_enabled=guild_data[9],
                        ai_thread_id=guild_data[10],
                        ai_temperature=guild_data[11],
                        ai_personality_traits=personality_traits
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

    def get_vault_currency(self, guild_id: int) -> int:
        """
        Get the current amount of currency in the guild's vault.

        Args:
            guild_id (int): Guild ID

        Returns:
            int: Current vault currency
        """
        sql = 'SELECT vault_currency FROM Guilds WHERE id = %s'

        try:
            result = self.execute_query(sql, (guild_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting vault currency for guild {guild_id}: {e}")
            return 0

    def update_vault_currency(self, guild_id: int, new_currency: int) -> bool:
        """
        Update the guild's vault currency amount.

        Args:
            guild_id (int): Guild ID
            new_currency (int): New currency amount

        Returns:
            bool: True if successful, False otherwise
        """
        sql = 'UPDATE Guilds SET vault_currency = %s WHERE id = %s'

        try:
            self.execute_query(sql, (new_currency, guild_id), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating vault currency for guild {guild_id}: {e}")
            return False

    def add_vault_currency(self, guild_id: int, amount: int) -> bool:
        """
        Add currency to the guild's vault.

        Args:
            guild_id (int): Guild ID
            amount (int): Amount to add

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            current = self.get_vault_currency(guild_id)
            return self.update_vault_currency(guild_id, current + amount)
        except Exception as e:
            self.logger.error(f"Error adding currency to vault for guild {guild_id}: {e}")
            return False

    def subtract_vault_currency(self, guild_id: int, amount: int) -> bool:
        """
        Subtract currency from the guild's vault.

        Args:
            guild_id (int): Guild ID
            amount (int): Amount to subtract

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            current = self.get_vault_currency(guild_id)
            new_amount = max(0, current - amount)  # Prevent negative values
            return self.update_vault_currency(guild_id, new_amount)
        except Exception as e:
            self.logger.error(f"Error subtracting currency from vault for guild {guild_id}: {e}")
            return False

    # AI-related methods
    def get_ai_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """
        Get AI settings for a guild.

        Args:
            guild_id (int): Guild ID

        Returns:
            Optional[Dict[str, Any]]: AI settings or None if not found
        """
        sql = """
            SELECT ai_enabled, ai_thread_id, ai_temperature, ai_personality_traits
            FROM Guilds 
            WHERE id = %s
        """

        try:
            result = self.execute_query(sql, (guild_id,))
            if result and len(result) > 0:
                data = result[0]
                personality_traits = None
                if data[3]:  # ai_personality_traits
                    try:
                        personality_traits = json.loads(data[3])
                    except json.JSONDecodeError:
                        personality_traits = {"humor_level": "high", "sarcasm_level": "medium", "nerd_level": "high",
                                              "friendliness": "high"}

                return {
                    'ai_enabled': data[0],
                    'ai_thread_id': data[1],
                    'ai_temperature': data[2],
                    'ai_personality_traits': personality_traits
                }
            return None
        except Exception as e:
            self.logger.error(f"Error getting AI settings for guild {guild_id}: {e}")
            return None

    def update_ai_settings(self, guild_id: int, ai_enabled: Optional[bool] = None,
                           ai_thread_id: Optional[str] = None, ai_temperature: Optional[float] = None,
                           ai_personality_traits: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update AI settings for a guild.

        Args:
            guild_id (int): Guild ID
            ai_enabled (Optional[bool]): Whether AI is enabled
            ai_thread_id (Optional[str]): AI thread ID
            ai_temperature (Optional[float]): AI temperature setting
            ai_personality_traits (Optional[Dict[str, Any]]): AI personality traits

        Returns:
            bool: True if successful, False otherwise
        """
        # Build dynamic SQL based on provided parameters
        updates = []
        values = []

        if ai_enabled is not None:
            updates.append("ai_enabled = %s")
            values.append(ai_enabled)

        if ai_thread_id is not None:
            updates.append("ai_thread_id = %s")
            values.append(ai_thread_id)

        if ai_temperature is not None:
            updates.append("ai_temperature = %s")
            values.append(ai_temperature)

        if ai_personality_traits is not None:
            updates.append("ai_personality_traits = %s")
            values.append(json.dumps(ai_personality_traits))

        if not updates:
            return True  # Nothing to update

        sql = f"UPDATE Guilds SET {', '.join(updates)} WHERE id = %s"
        values.append(guild_id)

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating AI settings for guild {guild_id}: {e}")
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