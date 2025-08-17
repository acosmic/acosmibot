from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from database import Database
from Dao.BaseDao import BaseDao
from Entities.LotteryEvent import LotteryEvent
import logging

class LotteryEventDao(BaseDao[LotteryEvent]):
    """
    Data Access Object for LotteryEvent entities.
    Provides methods to interact with the LotteryEvents table in the database.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the LotteryEventDao with connection parameters.
        
        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(LotteryEvent, "LotteryEvents", db)
        
        # Create the table if it doesn't exist
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> None:
        """
        Create the LotteryEvents table if it doesn't exist.
        """
        create_table_sql = '''
                           CREATE TABLE IF NOT EXISTS LotteryEvents \
                           ( \
                               id \
                               INT \
                               AUTO_INCREMENT \
                               PRIMARY \
                               KEY, \
                               message_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               start_time \
                               DATETIME \
                               NOT \
                               NULL, \
                               end_time \
                               DATETIME \
                               NOT \
                               NULL, \
                               credits \
                               BIGINT \
                               DEFAULT \
                               0, \
                               winner_id \
                               BIGINT \
                               DEFAULT \
                               0, \
                               guild_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               channel_id \
                               BIGINT \
                               NOT \
                               NULL \
                               DEFAULT \
                               0
                           ) \
                           '''
        self.create_table_if_not_exists(create_table_sql)

    def add_new_event(self, lottery_event: LotteryEvent) -> bool:
        """
        Add a new lottery event to the database.

        Args:
            lottery_event (LotteryEvent): Lottery event to add

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
              INSERT INTO LotteryEvents (id, message_id, start_time, end_time, credits, winner_id, guild_id, channel_id)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s) \
              """
        values = (
            lottery_event.id,
            lottery_event.message_id,
            lottery_event.start_time,
            lottery_event.end_time,
            lottery_event.credits,
            lottery_event.winner_id,
            lottery_event.guild_id,
            lottery_event.channel_id  # Add this
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding lottery event: {e}")
            return False

    def get_current_event(self, guild_id: Optional[int] = None) -> Optional[LotteryEvent]:
        """
        Get the current active lottery event.

        Args:
            guild_id (Optional[int], optional): Discord guild ID to filter by. Defaults to None.

        Returns:
            Optional[LotteryEvent]: Current event if found, None otherwise
        """
        if guild_id:
            sql = """
                  SELECT id, \
                         message_id, \
                         start_time, \
                         end_time, \
                         credits, \
                         winner_id, \
                         guild_id, \
                         channel_id
                  FROM LotteryEvents
                  WHERE end_time > NOW() \
                    AND guild_id = %s
                  ORDER BY start_time DESC LIMIT 1 \
                  """
            params = (guild_id,)
        else:
            sql = """
                  SELECT id, \
                         message_id, \
                         start_time, \
                         end_time, \
                         credits, \
                         winner_id, \
                         guild_id, \
                         channel_id
                  FROM LotteryEvents
                  WHERE end_time > NOW()
                  ORDER BY start_time DESC LIMIT 1 \
                  """
            params = None

        try:
            result = self.execute_query(sql, params)

            if result and len(result) > 0:
                event_data = result[0]
                return LotteryEvent(
                    event_data[0], event_data[1], event_data[2],
                    event_data[3], event_data[4], event_data[5],
                    event_data[6], event_data[7]  # Add channel_id
                )
            return None

        except Exception as e:
            self.logger.error(f"Error getting current event: {e}")
            return None

    def update_event(self, lottery_event: LotteryEvent) -> bool:
        """
        Update an existing lottery event.

        Args:
            lottery_event (LotteryEvent): Event to update

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
              UPDATE LotteryEvents
              SET message_id = %s, \
                  start_time = %s, \
                  end_time   = %s, \
                  credits    = %s,
                  winner_id  = %s, \
                  guild_id   = %s, \
                  channel_id = %s
              WHERE id = %s \
              """
        values = (
            lottery_event.message_id,
            lottery_event.start_time,
            lottery_event.end_time,
            lottery_event.credits,
            lottery_event.winner_id,
            lottery_event.guild_id,
            lottery_event.channel_id,  # Add this
            lottery_event.id
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating event: {e}")
            return False

    def delete_event(self, id: int) -> bool:
        """
        Delete a lottery event by its ID.
        
        Args:
            id (int): Event ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            DELETE FROM LotteryEvents
            WHERE id = %s
        """
        
        try:
            self.execute_query(sql, (id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting event: {e}")
            return False

    def get_total_credits(self, guild_id: Optional[int] = None) -> int:
        """
        Get the total amount of credits awarded in all lottery events.
        
        Args:
            guild_id (Optional[int], optional): Discord guild ID to filter by. Defaults to None.
            
        Returns:
            int: Total credits
        """
        if guild_id:
            sql = """
                SELECT SUM(credits) AS total_credits
                FROM LotteryEvents
                WHERE guild_id = %s
            """
            params = (guild_id,)
        else:
            sql = """
                SELECT SUM(credits) AS total_credits
                FROM LotteryEvents
            """
            params = None
        
        try:
            result = self.execute_query(sql, params)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total credits: {e}")
            return 0

    def get_all_current_events(self) -> List[LotteryEvent]:
        """
        Get all current active lottery events across all guilds.

        Returns:
            List[LotteryEvent]: List of all current active events
        """
        sql = """
              SELECT id, message_id, start_time, end_time, credits, winner_id, guild_id, channel_id
              FROM LotteryEvents
              WHERE end_time > NOW()
              ORDER BY start_time DESC \
              """

        try:
            results = self.execute_query(sql)

            events = []
            if results:
                for event_data in results:
                    events.append(LotteryEvent(
                        event_data[0], event_data[1], event_data[2],
                        event_data[3], event_data[4], event_data[5], event_data[6], event_data[7]
                    ))

            return events

        except Exception as e:
            self.logger.error(f"Error getting all current events: {e}")
            return []

    def save(self, lottery_event: LotteryEvent) -> Optional[LotteryEvent]:
        """
        Save a lottery event to the database (insert if new, update if exists).
        
        Args:
            lottery_event (LotteryEvent): Event to save
            
        Returns:
            Optional[LotteryEvent]: Saved event or None on error
        """
        try:
            # Check if event exists
            existing_event = self.get_event_by_id(lottery_event.id) if lottery_event.id else None
            
            if existing_event:
                # Update
                if self.update_event(lottery_event):
                    return lottery_event
            else:
                # Insert
                if self.add_new_event(lottery_event):
                    return lottery_event
            
            return None
        except Exception as e:
            self.logger.error(f"Error saving lottery event: {e}")
            return None
