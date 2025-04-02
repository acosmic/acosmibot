from typing import Optional, Union
from datetime import datetime
from Entities.BaseEntity import BaseEntity

class AI_Thread(BaseEntity):
    """
    AI_Thread entity representing an OpenAI thread in the database.
    Stores information about AI conversation threads.
    """
    
    def __init__(
        self, 
        discord_id: int, 
        thread_id: str, 
        temperature: float, 
        timestamp: Union[str, datetime]
    ) -> None:
        """
        Initialize an AI_Thread entity with the provided attributes.
        
        Args:
            discord_id (int): Discord user ID associated with the thread
            thread_id (str): OpenAI thread ID
            temperature (float): Temperature setting for the AI model
            timestamp (Union[str, datetime]): When the thread was created
        """
        self.discord_id = discord_id
        self.thread_id = thread_id
        self.temperature = temperature
        self.timestamp = timestamp

    @property
    def discord_id(self) -> int:
        """Discord user ID associated with the thread"""
        return self._discord_id
    
    @discord_id.setter
    def discord_id(self, value: int) -> None:
        """Set Discord user ID"""
        self._discord_id = value

    @property
    def thread_id(self) -> str:
        """OpenAI thread ID"""
        return self._thread_id
    
    @thread_id.setter
    def thread_id(self, value: str) -> None:
        """Set thread ID"""
        self._thread_id = value

    @property
    def temperature(self) -> float:
        """Temperature setting for the AI model"""
        return self._temperature
    
    @temperature.setter
    def temperature(self, value: float) -> None:
        """Set temperature"""
        self._temperature = value

    @property
    def timestamp(self) -> Union[str, datetime]:
        """When the thread was created"""
        return self._timestamp
    
    @timestamp.setter
    def timestamp(self, value: Union[str, datetime]) -> None:
        """Set timestamp"""
        self._timestamp = value
    
    def __str__(self) -> str:
        """String representation of the AI thread"""
        return f"AI_Thread(discord_id={self.discord_id}, thread_id={self.thread_id}, temperature={self.temperature})"