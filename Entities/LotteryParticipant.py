from typing import Optional
from Entities.BaseEntity import BaseEntity

class LotteryParticipant(BaseEntity):
    """
    LotteryParticipant entity representing a participant in a lottery event.
    Links a user to a specific lottery event.
    """
    
    def __init__(self, event_id: int, participant_id: int) -> None:
        """
        Initialize a LotteryParticipant entity with the provided attributes.
        
        Args:
            event_id (int): Lottery event ID
            participant_id (int): Discord user ID of the participant
        """
        self.event_id = event_id
        self.participant_id = participant_id

    @property
    def event_id(self) -> int:
        """Lottery event ID"""
        return self._event_id
    
    @event_id.setter
    def event_id(self, value: int) -> None:
        """Set lottery event ID"""
        self._event_id = value
    
    @property
    def participant_id(self) -> int:
        """Discord user ID of the participant"""
        return self._participant_id
    
    @participant_id.setter
    def participant_id(self, value: int) -> None:
        """Set participant's Discord user ID"""
        self._participant_id = value
    
    def __str__(self) -> str:
        """String representation of the lottery participant"""
        return f"LotteryParticipant(event_id={self.event_id}, participant_id={self.participant_id})"