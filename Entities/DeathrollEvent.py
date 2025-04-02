from typing import Optional
from Entities.BaseEntity import BaseEntity

class DeathrollEvent(BaseEntity):
    """
    DeathrollEvent entity representing a deathroll game event in the database.
    Stores information about deathroll games, including players and game state.
    """
    
    def __init__(
        self, 
        id: int, 
        initiator: int, 
        acceptor: int, 
        bet: int, 
        message_id: int, 
        current_roll: int, 
        current_player: int, 
        is_finished: bool
    ) -> None:
        """
        Initialize a DeathrollEvent entity with the provided attributes.
        
        Args:
            id (int): Deathroll event ID
            initiator (int): Discord user ID of the game initiator
            acceptor (int): Discord user ID of the game acceptor
            bet (int): Amount bet on the game
            message_id (int): Discord message ID associated with the game
            current_roll (int): Current roll value
            current_player (int): Discord user ID of the current player
            is_finished (bool): Whether the game is finished
        """
        self.id = id
        self.initiator = initiator
        self.acceptor = acceptor
        self.bet = bet
        self.message_id = message_id
        self.current_roll = current_roll
        self.current_player = current_player
        self.is_finished = is_finished

    @property
    def id(self) -> int:
        """Deathroll event ID"""
        return self._id
    
    @id.setter
    def id(self, value: int) -> None:
        """Set deathroll event ID"""
        self._id = value

    @property
    def initiator(self) -> int:
        """Discord user ID of the game initiator"""
        return self._initiator
    
    @initiator.setter
    def initiator(self, value: int) -> None:
        """Set initiator Discord user ID"""
        self._initiator = value

    @property
    def acceptor(self) -> int:
        """Discord user ID of the game acceptor"""
        return self._acceptor
    
    @acceptor.setter
    def acceptor(self, value: int) -> None:
        """Set acceptor Discord user ID"""
        self._acceptor = value

    @property
    def bet(self) -> int:
        """Amount bet on the game"""
        return self._bet
    
    @bet.setter
    def bet(self, value: int) -> None:
        """Set bet amount"""
        self._bet = value

    @property
    def message_id(self) -> int:
        """Discord message ID associated with the game"""
        return self._message_id

    @message_id.setter
    def message_id(self, value: int) -> None:
        """Set Discord message ID"""
        self._message_id = value

    @property
    def current_roll(self) -> int:
        """Current roll value"""
        return self._current_roll
    
    @current_roll.setter
    def current_roll(self, value: int) -> None:
        """Set current roll value"""
        self._current_roll = value

    @property
    def current_player(self) -> int:
        """Discord user ID of the current player"""
        return self._current_player
    
    @current_player.setter
    def current_player(self, value: int) -> None:
        """Set current player Discord user ID"""
        self._current_player = value

    @property
    def is_finished(self) -> bool:
        """Whether the game is finished"""
        return self._is_finished
    
    @is_finished.setter
    def is_finished(self, value: bool) -> None:
        """Set game finished status"""
        self._is_finished = value
    
    def __str__(self) -> str:
        """String representation of the deathroll event"""
        return f"DeathrollEvent(id={self.id}, initiator={self.initiator}, acceptor={self.acceptor}, bet={self.bet}, current_roll={self.current_roll}, is_finished={self.is_finished})"