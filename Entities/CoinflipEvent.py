from typing import Optional, Union
from datetime import datetime
from Entities.BaseEntity import BaseEntity

class CoinflipEvent(BaseEntity):
    """
    CoinflipEvent entity representing a coinflip game event in the database.
    Stores information about coinflip games, including results and winnings.
    """
    
    def __init__(
        self, 
        id: int, 
        discord_id: int, 
        guess: str, 
        result: str, 
        amount_won: int, 
        amount_lost: int, 
        timestamp: Union[str, datetime]
    ) -> None:
        """
        Initialize a CoinflipEvent entity with the provided attributes.
        
        Args:
            id (int): Coinflip event ID
            discord_id (int): Discord user ID who played the coinflip
            guess (str): User's guess (Heads or Tails)
            result (str): Actual result (Heads or Tails)
            amount_won (int): Amount won by the user
            amount_lost (int): Amount lost by the user
            timestamp (Union[str, datetime]): Event timestamp
        """
        self.id = id
        self.discord_id = discord_id
        self.guess = guess
        self.result = result
        self.amount_won = amount_won
        self.amount_lost = amount_lost
        self.timestamp = timestamp

    @property
    def id(self) -> int:
        """Coinflip event ID"""
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        """Set coinflip event ID"""
        self._id = value

    @property
    def discord_id(self) -> int:
        """Discord user ID who played the coinflip"""
        return self._discord_id

    @discord_id.setter
    def discord_id(self, value: int) -> None:
        """Set Discord user ID"""
        self._discord_id = value

    @property
    def guess(self) -> str:
        """User's guess (Heads or Tails)"""
        return self._guess

    @guess.setter
    def guess(self, value: str) -> None:
        """Set user's guess"""
        self._guess = value

    @property
    def result(self) -> str:
        """Actual result (Heads or Tails)"""
        return self._result

    @result.setter
    def result(self, value: str) -> None:
        """Set actual result"""
        self._result = value

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