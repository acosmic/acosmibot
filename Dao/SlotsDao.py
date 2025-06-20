from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from database import Database
from Dao.BaseDao import BaseDao
from Entities.SlotEvent import SlotEvent
import logging

class SlotsDao(BaseDao[SlotEvent]):
    """
    Data Access Object for SlotEvent entities.
    Provides methods to interact with the Slots table in the database.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the SlotsDao with connection parameters.
        
        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(SlotEvent, "Slots", db)
        
        # Create the table if it doesn't exist
        self._create_table_if_not_exists()
    
    def _create_table_if_not_exists(self) -> None:
        """
        Create the Slots table if it doesn't exist.
        """
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS Slots (
            id INT AUTO_INCREMENT PRIMARY KEY,
            discord_id BIGINT NOT NULL,
            slot1 VARCHAR(255) NOT NULL,
            slot2 VARCHAR(255) NOT NULL,
            slot3 VARCHAR(255) NOT NULL,
            bet_amount INT NOT NULL,
            amount_won INT NOT NULL,
            amount_lost INT NOT NULL,
            timestamp DATETIME NOT NULL
        )
        '''
        self.create_table_if_not_exists(create_table_sql)
    
    def add_new_event(self, slot_event: SlotEvent) -> bool:
        """
        Add a new slot event to the database.
        
        Args:
            slot_event (SlotEvent): Slot event to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            INSERT INTO Slots (discord_id, slot1, slot2, slot3, bet_amount, amount_won, amount_lost, timestamp) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            slot_event.discord_id,
            slot_event.slot1,
            slot_event.slot2,
            slot_event.slot3,
            slot_event.bet_amount,
            slot_event.amount_won,
            slot_event.amount_lost,
            slot_event.timestamp
        )
        
        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding slot event: {e}")
            return False

    def get_slot_wins(self, discord_id: int) -> int:
        """
        Get the number of slot wins for a user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            int: Number of wins
        """
        sql = """
            SELECT COUNT(*)
            FROM Slots
            WHERE discord_id = %s AND amount_won > 0
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting slot wins: {e}")
            return 0
    
    def get_slot_losses(self, discord_id: int) -> int:
        """
        Get the number of slot losses for a user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            int: Number of losses
        """
        sql = """
            SELECT COUNT(*)
            FROM Slots
            WHERE discord_id = %s AND amount_lost > 0
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting slot losses: {e}")
            return 0
    
    def get_total_slots(self, discord_id: int) -> int:
        """
        Get the total number of slot games played by a user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            int: Total number of games
        """
        sql = """
            SELECT COUNT(*)
            FROM Slots
            WHERE discord_id = %s
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total slots: {e}")
            return 0
    
    def get_total_won(self, discord_id: int) -> int:
        """
        Get the total amount won by a user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            int: Total amount won
        """
        sql = """
            SELECT SUM(amount_won)
            FROM Slots
            WHERE discord_id = %s
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total won: {e}")
            return 0
    
    def get_total_lost(self, discord_id: int) -> int:
        """
        Get the total amount lost by a user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            int: Total amount lost
        """
        sql = """
            SELECT SUM(amount_lost)
            FROM Slots
            WHERE discord_id = %s
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total lost: {e}")
            return 0

    def get_top_wins(self) -> List[Tuple]:
        """
        Get the top slot wins.
        
        Returns:
            List[Tuple]: List of top wins
        """
        sql = """
            SELECT u.discord_username,
                s.amount_won AS largest_single_win,
                s.timestamp AS win_timestamp
            FROM Slots s
            JOIN Users u ON s.discord_id = u.id
            WHERE (u.id, s.amount_won) IN (
                SELECT u.id,
                    MAX(s1.amount_won) AS max_win
                FROM Slots s1
                JOIN Users u ON s1.discord_id = u.id
                GROUP BY u.id
            )
            ORDER BY largest_single_win DESC
            LIMIT 5;
            """
        
        try:
            return self.execute_query(sql) or []
        except Exception as e:
            self.logger.error(f"Error getting top wins: {e}")
            return []
    
    def get_top_losses(self) -> List[Tuple]:
        """
        Get the top slot losses.
        
        Returns:
            List[Tuple]: List of top losses
        """
        sql = """
            SELECT u.discord_username,
                s.amount_lost AS largest_single_loss,
                s.timestamp AS loss_timestamp
            FROM Slots s
            JOIN Users u ON s.discord_id = u.id
            WHERE (u.id, s.amount_lost) IN (
                SELECT u.id,
                    MAX(s1.amount_lost) AS max_loss
                FROM Slots s1
                JOIN Users u ON s1.discord_id = u.id
                GROUP BY u.id
            )
            ORDER BY largest_single_loss DESC
            LIMIT 5;
            """
        
        try:
            return self.execute_query(sql) or []
        except Exception as e:
            self.logger.error(f"Error getting top losses: {e}")
            return []

    def get_total_spins(self) -> int:
        """
        Get the total number of slot spins across all users.
        
        Returns:
            int: Total number of spins
        """
        sql = """
            SELECT COUNT(*)
            FROM Slots
        """
        
        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total spins: {e}")
            return 0
    
    def save(self, slot_event: SlotEvent) -> Optional[SlotEvent]:
        """
        Save a slot event to the database (insert if new, update if exists).
        
        Args:
            slot_event (SlotEvent): Slot event to save
            
        Returns:
            Optional[SlotEvent]: Saved slot event or None on error
        """
        try:
            # For slot events, we usually just insert new ones
            if self.add_new_event(slot_event):
                return slot_event
            return None
        except Exception as e:
            self.logger.error(f"Error saving slot event: {e}")
            return None