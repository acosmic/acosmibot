from typing import Optional, Union
from datetime import datetime
from Entities.BaseEntity import BaseEntity


class GuildUser(BaseEntity):
    """
    GuildUser entity representing a user's data within a specific guild.
    Stores guild-specific user information, statistics, and game-related data.
    """

    def __init__(
            self,
            user_id: int,
            guild_id: int,
            name: str,
            nickname: Optional[str] = None,
            level: int = 0,
            streak: int = 0,
            highest_streak: int = 0,
            exp: int = 0,
            exp_gained: int = 0,
            exp_lost: int = 0,
            currency: int = 0,
            slots_free_spins_remaining: int = 0,
            slots_locked_bet_amount: int = 0,
            slots_bonus_total_won: int = 0,
            messages_sent: int = 0,
            reactions_sent: int = 0,
            joined_at: Union[str, datetime] = None,
            last_active: Union[str, datetime] = None,
            daily: int = 0,
            last_daily: Optional[Union[str, datetime]] = None,
            is_active: bool = True
    ) -> None:
        """
        Initialize a GuildUser entity with the provided attributes.

        Args:
            user_id (int): Discord user ID
            guild_id (int): Discord guild ID
            nickname (Optional[str], optional): User's nickname in this guild. Defaults to None.
            level (int, optional): User's level in this guild. Defaults to 0.
            streak (int, optional): User's current streak in this guild. Defaults to 0.
            highest_streak (int, optional): User's highest streak in this guild. Defaults to 0.
            exp (int, optional): User's total experience points in this guild. Defaults to 0.
            exp_gained (int, optional): Experience points gained in this guild. Defaults to 0.
            exp_lost (int, optional): Experience points lost in this guild. Defaults to 0.
            currency (int, optional): User's currency amount in this guild. Defaults to 0.
            slots_free_spins_remaining (int, optional): Free spins remaining in active bonus round. Defaults to 0.
            slots_locked_bet_amount (int, optional): Bet amount locked during bonus round. Defaults to 0.
            slots_bonus_total_won (int, optional): Total winnings accumulated during bonus round. Defaults to 0.
            messages_sent (int, optional): Number of messages sent in this guild. Defaults to 0.
            reactions_sent (int, optional): Number of reactions sent in this guild. Defaults to 0.
            joined_at (Union[str, datetime], optional): When user joined this guild. Defaults to None.
            last_active (Union[str, datetime], optional): Last active timestamp in this guild. Defaults to None.
            daily (int, optional): Daily status flag in this guild. Defaults to 0.
            last_daily (Optional[Union[str, datetime]], optional): Last daily timestamp in this guild. Defaults to None.
            is_active (bool, optional): Whether user is active in this guild. Defaults to True.
        """
        self.user_id = user_id
        self.guild_id = guild_id
        self.name = name
        self.nickname = nickname
        self.level = level
        self.streak = streak
        self.highest_streak = highest_streak
        self.exp = exp
        self.exp_gained = exp_gained
        self.exp_lost = exp_lost
        self.currency = currency
        self.slots_free_spins_remaining = slots_free_spins_remaining
        self.slots_locked_bet_amount = slots_locked_bet_amount
        self.slots_bonus_total_won = slots_bonus_total_won
        self.messages_sent = messages_sent
        self.reactions_sent = reactions_sent
        self.joined_at = joined_at
        self.last_active = last_active
        self.daily = daily
        self.last_daily = last_daily
        self.is_active = is_active

    @property
    def user_id(self) -> int:
        """User's Discord ID"""
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        """Set user's Discord ID"""
        self._user_id = value

    @property
    def guild_id(self) -> int:
        """Guild's Discord ID"""
        return self._guild_id

    @guild_id.setter
    def guild_id(self, value: int) -> None:
        """Set guild's Discord ID"""
        self._guild_id = value

    @property
    def name(self) -> Optional[str]:
        """User's name in this guild"""
        return self._name

    @name.setter
    def name(self, value: Optional[str]) -> None:
        """Set user's name in this guild"""
        self._name = value

    @property
    def nickname(self) -> Optional[str]:
        """User's nickname in this guild"""
        return self._nickname

    @nickname.setter
    def nickname(self, value: Optional[str]) -> None:
        """Set user's nickname in this guild"""
        self._nickname = value

    @property
    def level(self) -> int:
        """User's level in this guild"""
        return self._level

    @level.setter
    def level(self, value: int) -> None:
        """Set user's level in this guild"""
        self._level = value

    @property
    def streak(self) -> int:
        """User's current streak in this guild"""
        return self._streak

    @streak.setter
    def streak(self, value: int) -> None:
        """Set user's current streak in this guild"""
        self._streak = value

    @property
    def highest_streak(self) -> int:
        """User's highest streak in this guild"""
        return self._highest_streak

    @highest_streak.setter
    def highest_streak(self, value: int) -> None:
        """Set user's highest streak in this guild"""
        self._highest_streak = value

    @property
    def exp(self) -> int:
        """User's total experience points in this guild"""
        return self._exp

    @exp.setter
    def exp(self, value: int) -> None:
        """Set user's total experience points in this guild"""
        self._exp = value

    @property
    def exp_gained(self) -> int:
        """User's experience points gained in this guild"""
        return self._exp_gained

    @exp_gained.setter
    def exp_gained(self, value: int) -> None:
        """Set user's experience points gained in this guild"""
        self._exp_gained = value

    @property
    def exp_lost(self) -> int:
        """User's experience points lost in this guild"""
        return self._exp_lost

    @exp_lost.setter
    def exp_lost(self, value: int) -> None:
        """Set user's experience points lost in this guild"""
        self._exp_lost = value

    @property
    def currency(self) -> int:
        """User's currency amount in this guild"""
        return self._currency

    @currency.setter
    def currency(self, value: int) -> None:
        """Set user's currency amount in this guild"""
        self._currency = value

    @property
    def slots_free_spins_remaining(self) -> int:
        """Number of free spins remaining in active bonus round"""
        return self._slots_free_spins_remaining

    @slots_free_spins_remaining.setter
    def slots_free_spins_remaining(self, value: int) -> None:
        """Set number of free spins remaining"""
        self._slots_free_spins_remaining = value

    @property
    def slots_locked_bet_amount(self) -> int:
        """Bet amount locked during bonus round (0 if not in bonus)"""
        return self._slots_locked_bet_amount

    @slots_locked_bet_amount.setter
    def slots_locked_bet_amount(self, value: int) -> None:
        """Set locked bet amount for bonus round"""
        self._slots_locked_bet_amount = value

    @property
    def slots_bonus_total_won(self) -> int:
        """Cumulative winnings during current bonus round (paid at end)"""
        return self._slots_bonus_total_won

    @slots_bonus_total_won.setter
    def slots_bonus_total_won(self, value: int) -> None:
        """Set total bonus round winnings"""
        self._slots_bonus_total_won = value

    @property
    def messages_sent(self) -> int:
        """Number of messages sent by the user in this guild"""
        return self._messages_sent

    @messages_sent.setter
    def messages_sent(self, value: int) -> None:
        """Set number of messages sent by the user in this guild"""
        self._messages_sent = value

    @property
    def reactions_sent(self) -> int:
        """Number of reactions sent by the user in this guild"""
        return self._reactions_sent

    @reactions_sent.setter
    def reactions_sent(self, value: int) -> None:
        """Set number of reactions sent by the user in this guild"""
        self._reactions_sent = value

    @property
    def joined_at(self) -> Union[str, datetime]:
        """When user joined this guild"""
        return self._joined_at

    @joined_at.setter
    def joined_at(self, value: Union[str, datetime]) -> None:
        """Set when user joined this guild"""
        self._joined_at = value

    @property
    def last_active(self) -> Union[str, datetime]:
        """User's last active timestamp in this guild"""
        return self._last_active

    @last_active.setter
    def last_active(self, value: Union[str, datetime]) -> None:
        """Set user's last active timestamp in this guild"""
        self._last_active = value

    @property
    def daily(self) -> int:
        """User's daily status flag in this guild"""
        return self._daily

    @daily.setter
    def daily(self, value: int) -> None:
        """Set user's daily status flag in this guild"""
        self._daily = value

    @property
    def last_daily(self) -> Optional[Union[str, datetime]]:
        """User's last daily timestamp in this guild"""
        return self._last_daily

    @last_daily.setter
    def last_daily(self, value: Optional[Union[str, datetime]]) -> None:
        """Set user's last daily timestamp in this guild"""
        self._last_daily = value

    @property
    def is_active(self) -> bool:
        """Whether user is active in this guild"""
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        """Set user's active status in this guild"""
        self._is_active = value

    def __str__(self) -> str:
        """String representation of the guild user"""
        return f"GuildUser(user_id={self.user_id}, guild_id={self.guild_id}, level={self.level}, currency={self.currency})"