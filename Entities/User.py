from typing import Optional, Union, Any
from datetime import datetime
from Entities.BaseEntity import BaseEntity

class User(BaseEntity):
    """
    User entity representing a Discord user in the database.
    Stores user information, statistics, and game-related data.
    """
    
    def __init__(
        self, 
        id: int, 
        discord_username: str, 
        nickname: Optional[str] = None, 
        level: int = 0, 
        season_level: int = 0, 
        season_exp: int = 0,
        streak: int = 0, 
        highest_streak: int = 0, 
        exp: int = 0, 
        exp_gained: int = 0, 
        exp_lost: int = 0,
        currency: int = 0, 
        messages_sent: int = 0, 
        reactions_sent: int = 0, 
        created: Union[str, datetime] = None,
        last_active: Union[str, datetime] = None, 
        daily: int = 0, 
        last_daily: Optional[Union[str, datetime]] = None
    ) -> None:
        """
        Initialize a User entity with the provided attributes.
        
        Args:
            id (int): Discord user ID
            discord_username (str): Discord username
            nickname (Optional[str], optional): User's nickname. Defaults to None.
            level (int, optional): User's level. Defaults to 0.
            season_level (int, optional): User's season level. Defaults to 0.
            season_exp (int, optional): User's season experience points. Defaults to 0.
            streak (int, optional): User's current streak. Defaults to 0.
            highest_streak (int, optional): User's highest streak. Defaults to 0.
            exp (int, optional): User's total experience points. Defaults to 0.
            exp_gained (int, optional): Experience points gained. Defaults to 0.
            exp_lost (int, optional): Experience points lost. Defaults to 0.
            currency (int, optional): User's currency amount. Defaults to 0.
            messages_sent (int, optional): Number of messages sent. Defaults to 0.
            reactions_sent (int, optional): Number of reactions sent. Defaults to 0.
            created (Union[str, datetime], optional): Creation timestamp. Defaults to None.
            last_active (Union[str, datetime], optional): Last active timestamp. Defaults to None.
            daily (int, optional): Daily status flag. Defaults to 0.
            last_daily (Optional[Union[str, datetime]], optional): Last daily timestamp. Defaults to None.
        """
        self.id = id
        self.discord_username = discord_username
        self.nickname = nickname
        self.level = level
        self.season_level = season_level
        self.season_exp = season_exp
        self.streak = streak
        self.highest_streak = highest_streak
        self.exp = exp
        self.exp_gained = exp_gained
        self.exp_lost = exp_lost
        self.currency = currency
        self.messages_sent = messages_sent
        self.reactions_sent = reactions_sent
        self.created = created
        self.last_active = last_active
        self.daily = daily
        self.last_daily = last_daily

    @property
    def id(self) -> int:
        """User's Discord ID"""
        return self._id
    
    @id.setter
    def id(self, value: int) -> None:
        """Set user's Discord ID"""
        self._id = value
    
    @property
    def discord_username(self) -> str:
        """User's Discord username"""
        return self._discord_username
    
    @discord_username.setter
    def discord_username(self, value: str) -> None:
        """Set user's Discord username"""
        self._discord_username = value

    @property
    def nickname(self) -> Optional[str]:
        """User's nickname"""
        return self._nickname
    
    @nickname.setter
    def nickname(self, value: Optional[str]) -> None:
        """Set user's nickname"""
        self._nickname = value

    @property
    def level(self) -> int:
        """User's level"""
        return self._level
    
    @level.setter
    def level(self, value: int) -> None:
        """Set user's level"""
        self._level = value

    @property
    def season_level(self) -> int:
        """User's season level"""
        return self._season_level
    
    @season_level.setter
    def season_level(self, value: int) -> None:
        """Set user's season level"""
        self._season_level = value

    @property
    def season_exp(self) -> int:
        """User's season experience points"""
        return self._season_exp
    
    @season_exp.setter
    def season_exp(self, value: int) -> None:
        """Set user's season experience points"""
        self._season_exp = value

    @property
    def streak(self) -> int:
        """User's current streak"""
        return self._streak
    
    @streak.setter
    def streak(self, value: int) -> None:
        """Set user's current streak"""
        self._streak = value

    @property
    def highest_streak(self) -> int:
        """User's highest streak"""
        return self._highest_streak
    
    @highest_streak.setter
    def highest_streak(self, value: int) -> None:
        """Set user's highest streak"""
        self._highest_streak = value

    @property
    def exp(self) -> int:
        """User's total experience points"""
        return self._exp
    
    @exp.setter
    def exp(self, value: int) -> None:
        """Set user's total experience points"""
        self._exp = value

    @property
    def exp_gained(self) -> int:
        """User's experience points gained"""
        return self._exp_gained
    
    @exp_gained.setter
    def exp_gained(self, value: int) -> None:
        """Set user's experience points gained"""
        self._exp_gained = value

    @property
    def exp_lost(self) -> int:
        """User's experience points lost"""
        return self._exp_lost
    
    @exp_lost.setter
    def exp_lost(self, value: int) -> None:
        """Set user's experience points lost"""
        self._exp_lost = value

    @property
    def currency(self) -> int:
        """User's currency amount"""
        return self._currency
    
    @currency.setter
    def currency(self, value: int) -> None:
        """Set user's currency amount"""
        self._currency = value

    @property
    def messages_sent(self) -> int:
        """Number of messages sent by the user"""
        return self._messages_sent
    
    @messages_sent.setter
    def messages_sent(self, value: int) -> None:
        """Set number of messages sent by the user"""
        self._messages_sent = value

    @property
    def reactions_sent(self) -> int:
        """Number of reactions sent by the user"""
        return self._reactions_sent
    
    @reactions_sent.setter
    def reactions_sent(self, value: int) -> None:
        """Set number of reactions sent by the user"""
        self._reactions_sent = value

    @property
    def created(self) -> Union[str, datetime]:
        """User's creation timestamp"""
        return self._created
    
    @created.setter
    def created(self, value: Union[str, datetime]) -> None:
        """Set user's creation timestamp"""
        self._created = value

    @property
    def last_active(self) -> Union[str, datetime]:
        """User's last active timestamp"""
        return self._last_active
    
    @last_active.setter
    def last_active(self, value: Union[str, datetime]) -> None:
        """Set user's last active timestamp"""
        self._last_active = value

    @property
    def daily(self) -> int:
        """User's daily status flag"""
        return self._daily
    
    @daily.setter
    def daily(self, value: int) -> None:
        """Set user's daily status flag"""
        self._daily = value

    @property
    def last_daily(self) -> Optional[Union[str, datetime]]:
        """User's last daily timestamp"""
        return self._last_daily
    
    @last_daily.setter
    def last_daily(self, value: Optional[Union[str, datetime]]) -> None:
        """Set user's last daily timestamp"""
        self._last_daily = value
