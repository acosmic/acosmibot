from typing import Optional, Union
from datetime import datetime
from Entities.BaseEntity import BaseEntity

class Invite(BaseEntity):
    """
    Invite entity representing a Discord invite in the database.
    Stores information about invites, including who invited whom.
    """
    
    def __init__(
        self, 
        id: int, 
        guild_id: int, 
        inviter_id: int, 
        invitee_id: int, 
        code: str, 
        timestamp: Union[str, datetime]
    ) -> None:
        """
        Initialize an Invite entity with the provided attributes.
        
        Args:
            id (int): Invite ID
            guild_id (int): Discord guild (server) ID
            inviter_id (int): Discord user ID of the inviter
            invitee_id (int): Discord user ID of the invitee
            code (str): Discord invite code
            timestamp (Union[str, datetime]): When the invite was used
        """
        self.id = id
        self.guild_id = guild_id
        self.inviter_id = inviter_id
        self.invitee_id = invitee_id
        self.code = code
        self.timestamp = timestamp

    @property
    def id(self) -> int:
        """Invite ID"""
        return self._id
    
    @id.setter
    def id(self, value: int) -> None:
        """Set invite ID"""
        self._id = value
    
    @property
    def guild_id(self) -> int:
        """Discord guild (server) ID"""
        return self._guild_id
    
    @guild_id.setter
    def guild_id(self, value: int) -> None:
        """Set guild ID"""
        self._guild_id = value

    @property
    def inviter_id(self) -> int:
        """Discord user ID of the inviter"""
        return self._inviter_id
    
    @inviter_id.setter
    def inviter_id(self, value: int) -> None:
        """Set inviter ID"""
        self._inviter_id = value
    
    @property
    def invitee_id(self) -> int:
        """Discord user ID of the invitee"""
        return self._invitee_id
    
    @invitee_id.setter
    def invitee_id(self, value: int) -> None:
        """Set invitee ID"""
        self._invitee_id = value

    @property
    def code(self) -> str:
        """Discord invite code"""
        return self._code
    
    @code.setter
    def code(self, value: str) -> None:
        """Set invite code"""
        self._code = value

    @property
    def timestamp(self) -> Union[str, datetime]:
        """When the invite was used"""
        return self._timestamp
    
    @timestamp.setter
    def timestamp(self, value: Union[str, datetime]) -> None:
        """Set timestamp"""
        self._timestamp = value
    
    def __str__(self) -> str:
        """String representation of the invite"""
        return f"Invite(id={self.id}, inviter_id={self.inviter_id}, invitee_id={self.invitee_id}, code={self.code})"