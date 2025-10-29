#! /usr/bin/python3.10
from typing import Optional, Union
from datetime import datetime
from Entities.BaseEntity import BaseEntity


class CrossServerPortal(BaseEntity):
    """
    Entity representing a temporary cross-server portal session.
    Portals allow bidirectional messaging between two guilds for 2 minutes.
    """

    def __init__(
            self,
            id: Optional[int] = None,
            guild_id_1: int = 0,
            guild_id_2: int = 0,
            channel_id_1: int = 0,
            channel_id_2: int = 0,
            message_id_1: Optional[int] = None,
            message_id_2: Optional[int] = None,
            opened_by: int = 0,
            cost_paid: int = 1000,
            opened_at: Union[str, datetime, None] = None,
            closes_at: Union[str, datetime, None] = None,
            is_active: bool = True
    ) -> None:
        """
        Initialize a CrossServerPortal entity.

        Args:
            id: Unique portal session ID (auto-increment)
            guild_id_1: First guild ID (initiator)
            guild_id_2: Second guild ID (receiver)
            channel_id_1: Channel ID in first guild
            channel_id_2: Channel ID in second guild
            message_id_1: Portal embed message ID in first guild
            message_id_2: Portal embed message ID in second guild
            opened_by: User ID who opened/paid for the portal
            cost_paid: Amount of credits spent to open portal
            opened_at: When the portal was opened
            closes_at: When the portal will close (2 minutes from opened_at)
            is_active: Whether the portal is currently active
        """
        self._id = id
        self._guild_id_1 = guild_id_1
        self._guild_id_2 = guild_id_2
        self._channel_id_1 = channel_id_1
        self._channel_id_2 = channel_id_2
        self._message_id_1 = message_id_1
        self._message_id_2 = message_id_2
        self._opened_by = opened_by
        self._cost_paid = cost_paid
        self._opened_at = opened_at
        self._closes_at = closes_at
        self._is_active = is_active

    @property
    def id(self) -> Optional[int]:
        """Portal session ID"""
        return self._id

    @id.setter
    def id(self, value: Optional[int]):
        """Set portal session ID"""
        self._id = value

    @property
    def guild_id_1(self) -> int:
        """First guild ID (initiator)"""
        return self._guild_id_1

    @guild_id_1.setter
    def guild_id_1(self, value: int):
        """Set first guild ID"""
        self._guild_id_1 = value

    @property
    def guild_id_2(self) -> int:
        """Second guild ID (receiver)"""
        return self._guild_id_2

    @guild_id_2.setter
    def guild_id_2(self, value: int):
        """Set second guild ID"""
        self._guild_id_2 = value

    @property
    def channel_id_1(self) -> int:
        """Channel ID in first guild"""
        return self._channel_id_1

    @channel_id_1.setter
    def channel_id_1(self, value: int):
        """Set first channel ID"""
        self._channel_id_1 = value

    @property
    def channel_id_2(self) -> int:
        """Channel ID in second guild"""
        return self._channel_id_2

    @channel_id_2.setter
    def channel_id_2(self, value: int):
        """Set second channel ID"""
        self._channel_id_2 = value

    @property
    def message_id_1(self) -> Optional[int]:
        """Portal message ID in first guild"""
        return self._message_id_1

    @message_id_1.setter
    def message_id_1(self, value: Optional[int]):
        """Set first portal message ID"""
        self._message_id_1 = value

    @property
    def message_id_2(self) -> Optional[int]:
        """Portal message ID in second guild"""
        return self._message_id_2

    @message_id_2.setter
    def message_id_2(self, value: Optional[int]):
        """Set second portal message ID"""
        self._message_id_2 = value

    @property
    def opened_by(self) -> int:
        """User ID who opened the portal"""
        return self._opened_by

    @opened_by.setter
    def opened_by(self, value: int):
        """Set opener user ID"""
        self._opened_by = value

    @property
    def cost_paid(self) -> int:
        """Cost in credits paid to open portal"""
        return self._cost_paid

    @cost_paid.setter
    def cost_paid(self, value: int):
        """Set cost paid"""
        self._cost_paid = value

    @property
    def opened_at(self) -> Union[str, datetime, None]:
        """When the portal was opened"""
        return self._opened_at

    @opened_at.setter
    def opened_at(self, value: Union[str, datetime, None]):
        """Set opened timestamp"""
        self._opened_at = value

    @property
    def closes_at(self) -> Union[str, datetime, None]:
        """When the portal closes"""
        return self._closes_at

    @closes_at.setter
    def closes_at(self, value: Union[str, datetime, None]):
        """Set close timestamp"""
        self._closes_at = value

    @property
    def is_active(self) -> bool:
        """Whether the portal is currently active"""
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool):
        """Set active status"""
        self._is_active = value

    def __str__(self) -> str:
        """String representation of the portal"""
        return f"CrossServerPortal(id={self.id}, {self.guild_id_1}<->{self.guild_id_2}, active={self.is_active})"
