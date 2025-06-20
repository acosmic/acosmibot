from typing import Optional, List
from database import Database
from Dao.BaseDao import BaseDao
from Entities.DeathrollEvent import DeathrollEvent
import logging

class DeathrollDao(BaseDao[DeathrollEvent]):
    """
    Data Access Object for DeathrollEvent entities.
    Provides methods to interact with the DeathrollEvents table in the database.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the DeathrollDao with connection parameters.
        
        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(DeathrollEvent, "DeathrollEvents", db)
        
        # Create the table if it doesn't exist
        self._create_table_if_not_exists()
    
    def _create_table_if_not_exists(self) -> None:
        """
        Create the DeathrollEvents table if it doesn't exist.
        """
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS DeathrollEvents (
            id INT AUTO_INCREMENT PRIMARY KEY,
            initiator_id BIGINT NOT NULL,
            acceptor_id BIGINT NOT NULL,
            bet INT NOT NULL,
            message_id BIGINT NOT NULL,
            current_roll INT NOT NULL,
            current_player_id BIGINT NOT NULL,
            is_finished BOOLEAN NOT NULL DEFAULT FALSE
        )
        '''
        self.create_table_if_not_exists(create_table_sql)
    
    def add_new_event(self, deathroll_event: DeathrollEvent) -> bool:
        """
        Add a new deathroll event to the database.
        
        Args:
            deathroll_event (DeathrollEvent): Deathroll event to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            INSERT INTO DeathrollEvents (initiator_id, acceptor_id, bet, message_id, current_roll, current_player_id, is_finished) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            deathroll_event.initiator,
            deathroll_event.acceptor,
            deathroll_event.bet,
            deathroll_event.message_id,
            deathroll_event.current_roll,
            deathroll_event.current_player,
            deathroll_event.is_finished
        )
        
        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding deathroll event: {e}")
            return False

    def get_event(self, message_id: int) -> Optional[DeathrollEvent]:
        """
        Get a deathroll event by its message ID.
        
        Args:
            message_id (int): Discord message ID
            
        Returns:
            Optional[DeathrollEvent]: Event if found, None otherwise
        """
        sql = """
            SELECT id, initiator_id, acceptor_id, bet, message_id, current_roll, current_player_id, is_finished
            FROM DeathrollEvents
            WHERE message_id = %s
        """
        
        try:
            result = self.execute_query(sql, (message_id,))
            
            if result and len(result) > 0:
                event_data = result[0]
                return DeathrollEvent(
                    event_data[0], event_data[1], event_data[2], 
                    event_data[3], event_data[4], event_data[5], 
                    event_data[6], bool(event_data[7])
                )
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting deathroll event: {e}")
            return None

    def check_if_user_ingame(self, initiator_id: int, acceptor_id: int) -> List[DeathrollEvent]:
        """
        Check if either user is currently in an unfinished deathroll game.
        
        Args:
            initiator_id (int): Initiator's Discord user ID
            acceptor_id (int): Acceptor's Discord user ID
            
        Returns:
            List[DeathrollEvent]: List of active events involving either user
        """
        sql = """
            SELECT id, initiator_id, acceptor_id, bet, message_id, current_roll, current_player_id, is_finished
            FROM DeathrollEvents
            WHERE (initiator_id = %s OR acceptor_id = %s OR initiator_id = %s OR acceptor_id = %s)
            AND is_finished = FALSE
        """
        
        try:
            results = self.execute_query(sql, (initiator_id, initiator_id, acceptor_id, acceptor_id))
            
            events = []
            if results:
                for event_data in results:
                    events.append(DeathrollEvent(
                        event_data[0], event_data[1], event_data[2], 
                        event_data[3], event_data[4], event_data[5], 
                        event_data[6], bool(event_data[7])
                    ))
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error checking if user is in game: {e}")
            return []

    def update_event(self, deathroll_event: DeathrollEvent) -> bool:
        """
        Update an existing deathroll event.
        
        Args:
            deathroll_event (DeathrollEvent): Event to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            UPDATE DeathrollEvents
            SET current_roll = %s, current_player_id = %s, is_finished = %s
            WHERE message_id = %s
        """
        values = (
            deathroll_event.current_roll,
            deathroll_event.current_player,
            deathroll_event.is_finished,
            deathroll_event.message_id
        )
        
        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating deathroll event: {e}")
            return False

    def delete_event(self, message_id: int) -> bool:
        """
        Delete a deathroll event by its message ID.
        
        Args:
            message_id (int): Discord message ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            DELETE FROM DeathrollEvents
            WHERE message_id = %s
        """
        
        try:
            self.execute_query(sql, (message_id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting deathroll event: {e}")
            return False

    def get_all_events(self) -> List[DeathrollEvent]:
        """
        Get all deathroll events.
        
        Returns:
            List[DeathrollEvent]: List of all events
        """
        sql = """
            SELECT id, initiator_id, acceptor_id, bet, message_id, current_roll, current_player_id, is_finished
            FROM DeathrollEvents
        """
        
        try:
            results = self.execute_query(sql)
            
            events = []
            if results:
                for event_data in results:
                    events.append(DeathrollEvent(
                        event_data[0], event_data[1], event_data[2], 
                        event_data[3], event_data[4], event_data[5], 
                        event_data[6], bool(event_data[7])
                    ))
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error getting all deathroll events: {e}")
            return []
    
    def get_active_games_count(self) -> int:
        """
        Get the count of active (unfinished) deathroll games.
        
        Returns:
            int: Number of active games
        """
        sql = """
            SELECT COUNT(*)
            FROM DeathrollEvents
            WHERE is_finished = FALSE
        """
        
        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting active games count: {e}")
            return 0
    
    def get_user_games(self, user_id: int, include_finished: bool = False) -> List[DeathrollEvent]:
        """
        Get all deathroll games for a specific user.
        
        Args:
            user_id (int): User's Discord ID
            include_finished (bool, optional): Whether to include finished games. Defaults to False.
            
        Returns:
            List[DeathrollEvent]: List of user's games
        """
        if include_finished:
            sql = """
                SELECT id, initiator_id, acceptor_id, bet, message_id, current_roll, current_player_id, is_finished
                FROM DeathrollEvents
                WHERE initiator_id = %s OR acceptor_id = %s
            """
        else:
            sql = """
                SELECT id, initiator_id, acceptor_id, bet, message_id, current_roll, current_player_id, is_finished
                FROM DeathrollEvents
                WHERE (initiator_id = %s OR acceptor_id = %s) AND is_finished = FALSE
            """
        
        try:
            results = self.execute_query(sql, (user_id, user_id))
            
            events = []
            if results:
                for event_data in results:
                    events.append(DeathrollEvent(
                        event_data[0], event_data[1], event_data[2], 
                        event_data[3], event_data[4], event_data[5], 
                        event_data[6], bool(event_data[7])
                    ))
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error getting user games: {e}")
            return []
    
    def save(self, deathroll_event: DeathrollEvent) -> Optional[DeathrollEvent]:
        """
        Save a deathroll event to the database (insert if new, update if exists).
        
        Args:
            deathroll_event (DeathrollEvent): Deathroll event to save
            
        Returns:
            Optional[DeathrollEvent]: Saved event or None on error
        """
        try:
            # Check if the event exists by message_id
            existing_event = self.get_event(deathroll_event.message_id)
            
            if existing_event:
                # Update
                if self.update_event(deathroll_event):
                    return deathroll_event
            else:
                # Insert
                if self.add_new_event(deathroll_event):
                    return deathroll_event
            
            return None
        except Exception as e:
            self.logger.error(f"Error saving deathroll event: {e}")
            return None