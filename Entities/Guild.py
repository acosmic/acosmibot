# Entities/Guild.py
from typing import Optional, Union, Any
from datetime import datetime
from Entities.BaseEntity import BaseEntity


class Guild(BaseEntity):
    """
    Guild entity representing a Discord guild in the database.
    """

    def __init__(
            self,
            id: int,
            name: str,
            owner_id: int,
            member_count: int = 0,
            active: bool = True,
            settings: Optional[str] = None,
            created: Union[str, datetime] = None,
            last_active: Union[str, datetime] = None
    ) -> None:
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.member_count = member_count
        self.active = active
        self.settings = settings
        self.created = created
        self.last_active = last_active

    @property
    def id(self) -> int:
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        self._id = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def owner_id(self) -> int:
        return self._owner_id

    @owner_id.setter
    def owner_id(self, value: int) -> None:
        self._owner_id = value

    @property
    def member_count(self) -> int:
        return self._member_count

    @member_count.setter
    def member_count(self, value: int) -> None:
        self._member_count = value

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value

    @property
    def settings(self) -> Optional[str]:
        return self._settings

    @settings.setter
    def settings(self, value: Optional[str]) -> None:
        self._settings = value

    @property
    def created(self) -> Union[str, datetime]:
        return self._created

    @created.setter
    def created(self, value: Union[str, datetime]) -> None:
        self._created = value

    @property
    def last_active(self) -> Union[str, datetime]:
        return self._last_active

    @last_active.setter
    def last_active(self, value: Union[str, datetime]) -> None:
        self._last_active = value