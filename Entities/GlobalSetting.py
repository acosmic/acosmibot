#! /usr/bin/python3.10
"""
GlobalSetting Entity
Represents a global bot setting
"""

from typing import Optional, Any
from datetime import datetime
from Entities.BaseEntity import BaseEntity


class GlobalSetting(BaseEntity):
    """Entity representing a global bot setting"""

    def __init__(
        self,
        id: Optional[int] = None,
        setting_key: Optional[str] = None,
        value: Optional[Any] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        updated_at: Optional[datetime] = None
    ):
        """
        Initialize GlobalSetting entity

        Args:
            id: Setting ID (primary key)
            setting_key: Unique key for the setting
            value: Setting value (can be any type)
            category: Category this setting belongs to
            description: Human-readable description
            updated_at: When the setting was last updated
        """
        self._id = id
        self._setting_key = setting_key
        self._value = value
        self._category = category
        self._description = description
        self._updated_at = updated_at

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def setting_key(self) -> Optional[str]:
        return self._setting_key

    @property
    def value(self) -> Optional[Any]:
        return self._value

    @property
    def category(self) -> Optional[str]:
        return self._category

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def updated_at(self) -> Optional[datetime]:
        return self._updated_at
