#! /usr/bin/python3.10
"""
AdminUser Entity
Represents an admin user in the system
"""

from typing import Optional
from datetime import datetime
from Entities.BaseEntity import BaseEntity


class AdminUser(BaseEntity):
    """Entity representing an admin user"""

    def __init__(
        self,
        id: Optional[int] = None,
        discord_id: Optional[str] = None,
        discord_username: Optional[str] = None,
        role: Optional[str] = None,
        created_at: Optional[datetime] = None,
        created_by: Optional[str] = None
    ):
        """
        Initialize AdminUser entity

        Args:
            id: Admin user ID (primary key)
            discord_id: Discord user ID
            discord_username: Discord username
            role: Admin role ('admin' or 'super_admin')
            created_at: When the admin was created
            created_by: Discord ID of who created this admin
        """
        self._id = id
        self._discord_id = discord_id
        self._discord_username = discord_username
        self._role = role
        self._created_at = created_at
        self._created_by = created_by

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def discord_id(self) -> Optional[str]:
        return self._discord_id

    @property
    def discord_username(self) -> Optional[str]:
        return self._discord_username

    @property
    def role(self) -> Optional[str]:
        return self._role

    @property
    def created_at(self) -> Optional[datetime]:
        return self._created_at

    @property
    def created_by(self) -> Optional[str]:
        return self._created_by
