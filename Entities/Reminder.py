from typing import Optional, Union
from datetime import datetime, timedelta, timezone
from Entities.BaseEntity import BaseEntity


class Reminder(BaseEntity):
    """
    Reminder entity representing a user reminder in the database.
    Stores information about scheduled reminders including timing and message content.
    """

    def __init__(
            self,
            id: Optional[int] = None,
            user_id: int = 0,
            guild_id: int = 0,
            channel_id: int = 0,
            message: str = "",
            remind_at: Union[str, datetime, None] = None,
            created_at: Union[str, datetime, None] = None,
            completed: bool = False,
            message_url: str = ""
    ) -> None:
        """
        Initialize a Reminder entity with the provided attributes.

        Args:
            id (Optional[int]): Database ID of the reminder
            user_id (int): Discord user ID who set the reminder
            guild_id (int): Discord guild ID where reminder was set
            channel_id (int): Discord channel ID where reminder was set
            message (str): Reminder message content
            remind_at (Union[str, datetime, None]): When to send the reminder
            created_at (Union[str, datetime, None]): When the reminder was created
            completed (bool): Whether the reminder has been sent
            message_url (str): URL to the original message where reminder was set
        """
        self.id = id
        self.user_id = user_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.message = message
        self.remind_at = remind_at if remind_at else datetime.now(timezone.utc)
        self.created_at = created_at if created_at else datetime.now(timezone.utc)
        self.completed = completed
        self.message_url = message_url

    @property
    def id(self) -> Optional[int]:
        """Database ID of the reminder"""
        return self._id

    @id.setter
    def id(self, value: Optional[int]) -> None:
        """Set reminder ID"""
        self._id = value

    @property
    def user_id(self) -> int:
        """Discord user ID who set the reminder"""
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        """Set user ID"""
        self._user_id = value

    @property
    def guild_id(self) -> int:
        """Discord guild ID where reminder was set"""
        return self._guild_id

    @guild_id.setter
    def guild_id(self, value: int) -> None:
        """Set guild ID"""
        self._guild_id = value

    @property
    def channel_id(self) -> int:
        """Discord channel ID where reminder was set"""
        return self._channel_id

    @channel_id.setter
    def channel_id(self, value: int) -> None:
        """Set channel ID"""
        self._channel_id = value

    @property
    def message(self) -> str:
        """Reminder message content"""
        return self._message

    @message.setter
    def message(self, value: str) -> None:
        """Set reminder message"""
        self._message = value

    @property
    def remind_at(self) -> datetime:
        """When to send the reminder"""
        return self._remind_at

    @remind_at.setter
    def remind_at(self, value: Union[str, datetime]) -> None:
        """Set reminder time"""
        if isinstance(value, str):
            self._remind_at = datetime.fromisoformat(value)
        else:
            self._remind_at = value

    @property
    def created_at(self) -> datetime:
        """When the reminder was created"""
        return self._created_at

    @created_at.setter
    def created_at(self, value: Union[str, datetime]) -> None:
        """Set creation time"""
        if isinstance(value, str):
            self._created_at = datetime.fromisoformat(value)
        else:
            self._created_at = value

    @property
    def completed(self) -> bool:
        """Whether the reminder has been sent"""
        return self._completed

    @completed.setter
    def completed(self, value: bool) -> None:
        """Set completion status"""
        self._completed = value

    @property
    def message_url(self) -> str:
        """URL to the original message where reminder was set"""
        return self._message_url

    @message_url.setter
    def message_url(self, value: str) -> None:
        """Set message URL"""
        self._message_url = value if value else ""

    def __str__(self) -> str:
        """String representation of the reminder"""
        return (f"Reminder(id={self.id}, user_id={self.user_id}, "
                f"message='{self.message[:30]}...', remind_at={self.remind_at}, "
                f"completed={self.completed})")

    def is_due(self) -> bool:
        """
        Check if the reminder is due to be sent.

        Returns:
            bool: True if reminder should be sent now, False otherwise
        """
        return not self.completed and self.remind_at <= datetime.now(timezone.utc)

    def time_until_due(self) -> Optional[float]:
        """
        Calculate seconds until the reminder is due.

        Returns:
            Optional[float]: Seconds until due, or None if already completed
        """
        if self.completed:
            return None

        delta = self.remind_at - datetime.now(timezone.utc)
        return max(0, delta.total_seconds())