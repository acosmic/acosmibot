from typing import Optional, List
from database import Database
from Dao.BaseDao import BaseDao
from Entities.LotteryParticipant import LotteryParticipant
import logging

class LotteryParticipantDao(BaseDao[LotteryParticipant]):
    """
    Data Access Object for LotteryParticipant entities.
    Provides methods to interact with the LotteryParticipants table in the database.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the LotteryParticipantDao with connection parameters.
        
        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(LotteryParticipant, "LotteryParticipants", db)
        
        # Create the table if it doesn't exist
        self._create_table_if_not_exists()
    
    def _create_table_if_not_exists(self) -> None:
        """
        Create the LotteryParticipants table if it doesn't exist.
        """
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS LotteryParticipants (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_id BIGINT NOT NULL,
            participant_id BIGINT NOT NULL,
            UNIQUE KEY (event_id, participant_id)
        )
        '''
        self.create_table_if_not_exists(create_table_sql)
    
    def add_new_participant(self, lottery_participant: LotteryParticipant) -> bool:
        """
        Add a new lottery participant to the database.
        
        Args:
            lottery_participant (LotteryParticipant): Lottery participant to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            INSERT INTO LotteryParticipants (event_id, participant_id)
            VALUES (%s, %s)
        """
        values = (
            lottery_participant.event_id,
            lottery_participant.participant_id
        )
        
        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding lottery participant: {e}")
            return False
    
    def get_participants(self, event_id: int) -> List[LotteryParticipant]:
        """
        Get all participants for a specific lottery event.
        
        Args:
            event_id (int): Lottery event ID
            
        Returns:
            List[LotteryParticipant]: List of participants
        """
        sql = """
            SELECT event_id, participant_id
            FROM LotteryParticipants
            WHERE event_id = %s
        """
        
        try:
            results = self.execute_query(sql, (event_id,))
            
            participants = []
            if results:
                for participant_data in results:
                    participants.append(LotteryParticipant(
                        participant_data[0], participant_data[1]
                    ))
            
            return participants
            
        except Exception as e:
            self.logger.error(f"Error getting participants: {e}")
            return []
    
    def get_all_participants(self) -> List[LotteryParticipant]:
        """
        Get all lottery participants across all events.
        
        Returns:
            List[LotteryParticipant]: List of all participants
        """
        sql = """
            SELECT event_id, participant_id
            FROM LotteryParticipants
        """
        
        try:
            results = self.execute_query(sql)
            
            participants = []
            if results:
                for participant_data in results:
                    participants.append(LotteryParticipant(
                        participant_data[0], participant_data[1]
                    ))
            
            return participants
            
        except Exception as e:
            self.logger.error(f"Error getting all participants: {e}")
            return []
    
    def get_participant(self, event_id: int, participant_id: int) -> Optional[LotteryParticipant]:
        """
        Get a specific participant for a specific event.
        
        Args:
            event_id (int): Event ID
            participant_id (int): Participant ID
            
        Returns:
            Optional[LotteryParticipant]: Participant if found, None otherwise
        """
        sql = """
            SELECT event_id, participant_id
            FROM LotteryParticipants
            WHERE event_id = %s AND participant_id = %s
        """
        
        try:
            result = self.execute_query(sql, (event_id, participant_id))
            
            if result and len(result) > 0:
                participant_data = result[0]
                return LotteryParticipant(
                    participant_data[0], participant_data[1]
                )
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting participant: {e}")
            return None
    
    def remove_participant(self, event_id: int, participant_id: int) -> bool:
        """
        Remove a specific participant from a specific event.
        
        Args:
            event_id (int): Event ID
            participant_id (int): Participant ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            DELETE FROM LotteryParticipants
            WHERE event_id = %s AND participant_id = %s
        """
        
        try:
            self.execute_query(sql, (event_id, participant_id), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error removing participant: {e}")
            return False

    def remove_all_participants(self, event_id: int) -> bool:
        """
        Remove all participants from a specific event.
        
        Args:
            event_id (int): Event ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            DELETE FROM LotteryParticipants
            WHERE event_id = %s
        """
        
        try:
            self.execute_query(sql, (event_id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error removing all participants: {e}")
            return False

    def remove_all_participants_by_participant_id(self, participant_id: int) -> bool:
        """
        Remove a specific participant from all events.
        
        Args:
            participant_id (int): Participant ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            DELETE FROM LotteryParticipants
            WHERE participant_id = %s
        """
        
        try:
            self.execute_query(sql, (participant_id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error removing participant from all events: {e}")
            return False
    
    def save(self, lottery_participant: LotteryParticipant) -> Optional[LotteryParticipant]:
        """
        Save a lottery participant to the database (insert only, as we don't update lottery participants).
        
        Args:
            lottery_participant (LotteryParticipant): Lottery participant to save
            
        Returns:
            Optional[LotteryParticipant]: Saved lottery participant or None on error
        """
        try:
            if self.add_new_participant(lottery_participant):
                return lottery_participant
            return None
        except Exception as e:
            self.logger.error(f"Error saving lottery participant: {e}")
            return None