from typing import Optional, Union
from datetime import datetime
from Entities.BaseEntity import BaseEntity

class SlotEvent(BaseEntity):
    """
    SlotEvent entity representing a slot game event in the database.
    Stores information about slot games, including results and winnings.
    """
    
    def __init__(
        self, 
        id: int, 
        discord_id: int, 
        slot1: str, 
        slot2: str, 
        slot3: str, 
        bet_amount: int, 
        amount_won: int, 
        amount_lost: int, 
        timestamp: Union[str, datetime]
    ) -> None:
        """
        Initialize a SlotEvent entity with the provided attributes.
        
        Args:
            id (int): Slot event ID
            discord_id (int): Discord user ID who played the slot
            slot1 (str): First slot result
            slot2 (str): Second slot result
            slot3 (str): Third slot result
            bet_amount (int): Amount bet by the user
            amount_won (int): Amount won by the user
            amount_lost (int): Amount lost by the user
            timestamp (Union[str, datetime]): Event timestamp
        """
        self.id = id
        self.discord_id = discord_id
        self.slot1 = slot1
        self.slot2 = slot2
        self.slot3 = slot3
        self.bet_amount = bet_amount
        self.amount_won = amount_won
        self.amount_lost = amount_lost
        self.timestamp = timestamp

    @property
    def id(self) -> int:
        """Slot event ID"""
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        """Set slot event ID"""
        self._id = value

    @property
    def discord_id(self) -> int:
        """Discord user ID who played the slot"""
        return self._discord_id

    @discord_id.setter
    def discord_id(self, value: int) -> None:
        """Set Discord user ID"""
        self._discord_id = value

    @property
    def slot1(self) -> str:
        """First slot result"""
        return self._slot1

    @slot1.setter
    def slot1(self, value: str) -> None:
        """Set first slot result"""
        self._slot1 = value

    @property
    def slot2(self) -> str:
        """Second slot result"""
        return self._slot2

    @slot2.setter
    def slot2(self, value: str) -> None:
        """Set second slot result"""
        self._slot2 = value

    @property
    def slot3(self) -> str:
        """Third slot result"""
        return self._slot3

    @slot3.setter
    def slot3(self, value: str) -> None:
        """Set third slot result"""
        self._slot3 = value

    @property
    def bet_amount(self) -> int:
        """Amount bet by the user"""
        return self._bet_amount
    
    @bet_amount.setter
    def bet_amount(self, value: int) -> None:
        """Set bet amount"""
        self._bet_amount = value

    @property
    def amount_won(self) -> int:
        """Amount won by the user"""
        return self._amount_won

    @amount_won.setter
    def amount_won(self, value: int) -> None:
        """Set amount won"""
        self._amount_won = value

    @property
    def amount_lost(self) -> int:
        """Amount lost by the user"""
        return self._amount_lost

    @amount_lost.setter
    def amount_lost(self, value: int) -> None:
        """Set amount lost"""
        self._amount_lost = value

    @property
    def timestamp(self) -> Union[str, datetime]:
        """Event timestamp"""
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: Union[str, datetime]) -> None:
        """Set event timestamp"""
        self._timestamp = value