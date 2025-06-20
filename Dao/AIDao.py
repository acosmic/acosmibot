from typing import Optional, List
from datetime import datetime
from database import Database
from Dao.BaseDao import BaseDao
from Entities.AI_Thread import AI_Thread
import logging

class AIDao(BaseDao[AI_Thread]):
    """
    Data Access Object for AI_Thread entities.
    Provides methods to interact with the ai_threads table in the database.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the AIDao with connection parameters.
        
        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(AI_Thread, "ai_threads", db)
        
        # Create the table if it doesn't exist
        self._create_table_if_not_exists()
    
    def _create_table_if_not_exists(self) -> None:
        """
        Create the ai_threads table if it doesn't exist.
        """
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS ai_threads (
            discord_id BIGINT PRIMARY KEY,
            thread_id VARCHAR(255) NOT NULL,
            temperature FLOAT NOT NULL DEFAULT 1.0,
            timestamp DATETIME NOT NULL
        )
        '''
        self.create_table_if_not_exists(create_table_sql)
    
    def add_new_thread(self, discord_id: int, thread_id: str, temperature: float) -> bool:
        """
        Add a new AI thread to the database.
        
        Args:
            discord_id (int): Discord user ID
            thread_id (str): OpenAI thread ID
            temperature (float): Temperature setting
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            INSERT INTO ai_threads (discord_id, thread_id, temperature, timestamp)
            VALUES (%s, %s, %s, NOW())
        """
        values = (discord_id, thread_id, temperature)
        
        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding AI thread: {e}")
            return False

    def get_thread_id(self, discord_id: int) -> Optional[str]:
        """
        Get the thread ID for a specific Discord user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            Optional[str]: Thread ID if found, None otherwise
        """
        sql = """
            SELECT thread_id
            FROM ai_threads
            WHERE discord_id = %s
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else None
        except Exception as e:
            self.logger.error(f"Error getting thread ID: {e}")
            return None
    
    def get_thread(self, discord_id: int) -> Optional[AI_Thread]:
        """
        Get the AI thread for a specific Discord user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            Optional[AI_Thread]: Thread if found, None otherwise
        """
        sql = """
            SELECT discord_id, thread_id, temperature, timestamp
            FROM ai_threads
            WHERE discord_id = %s
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            
            if result and len(result) > 0:
                thread_data = result[0]
                return AI_Thread(
                    thread_data[0], thread_data[1], thread_data[2], thread_data[3]
                )
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting thread: {e}")
            return None
    
    def delete_thread(self, discord_id: int) -> bool:
        """
        Delete the AI thread for a specific Discord user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            DELETE FROM ai_threads
            WHERE discord_id = %s
        """
        
        try:
            self.execute_query(sql, (discord_id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting thread: {e}")
            return False
    
    def get_all_thread_ids(self) -> List[str]:
        """
        Get all thread IDs from the database.
        
        Returns:
            List[str]: List of thread IDs
        """
        sql = """
            SELECT thread_id
            FROM ai_threads
        """
        
        try:
            results = self.execute_query(sql)
            return [result[0] for result in results] if results else []
        except Exception as e:
            self.logger.error(f"Error getting all thread IDs: {e}")
            return []
    
    def get_all_discord_ids(self) -> List[int]:
        """
        Get all Discord user IDs from the database.
        
        Returns:
            List[int]: List of Discord user IDs
        """
        sql = """
            SELECT discord_id
            FROM ai_threads
        """
        
        try:
            results = self.execute_query(sql)
            return [result[0] for result in results] if results else []
        except Exception as e:
            self.logger.error(f"Error getting all Discord IDs: {e}")
            return []
    
    def update_thread_id(self, discord_id: int, thread_id: str) -> bool:
        """
        Update the thread ID for a specific Discord user.
        
        Args:
            discord_id (int): Discord user ID
            thread_id (str): New OpenAI thread ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            UPDATE ai_threads
            SET thread_id = %s, timestamp = NOW()
            WHERE discord_id = %s
        """
        
        try:
            self.execute_query(sql, (thread_id, discord_id), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating thread ID: {e}")
            return False
    
    def update_temperature(self, discord_id: int, temperature: float) -> bool:
        """
        Update the temperature setting for a specific Discord user.
        
        Args:
            discord_id (int): Discord user ID
            temperature (float): New temperature setting
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            UPDATE ai_threads
            SET temperature = %s
            WHERE discord_id = %s
        """
        
        try:
            self.execute_query(sql, (temperature, discord_id), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating temperature: {e}")
            return False

    def get_thread_count(self) -> int:
        """
        Get the total number of AI threads.
        
        Returns:
            int: Number of threads
        """
        sql = """
            SELECT COUNT(*)
            FROM ai_threads
        """
        
        try:
            result = self.execute_query(sql)
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting thread count: {e}")
            return 0
    
    def save(self, ai_thread: AI_Thread) -> Optional[AI_Thread]:
        """
        Save an AI thread to the database (insert if new, update if exists).
        
        Args:
            ai_thread (AI_Thread): AI thread to save
            
        Returns:
            Optional[AI_Thread]: Saved AI thread or None on error
        """
        try:
            # Check if the thread exists by discord_id
            existing_thread = self.get_thread(ai_thread.discord_id)
            
            if existing_thread:
                # Update thread_id and temperature
                if (self.update_thread_id(ai_thread.discord_id, ai_thread.thread_id) and 
                    self.update_temperature(ai_thread.discord_id, ai_thread.temperature)):
                    return ai_thread
            else:
                # Insert
                if self.add_new_thread(ai_thread.discord_id, ai_thread.thread_id, ai_thread.temperature):
                    return ai_thread
            
            return None
        except Exception as e:
            self.logger.error(f"Error saving AI thread: {e}")
            return None