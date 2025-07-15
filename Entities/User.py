from typing import Optional, Union, Any
from datetime import datetime
from Entities.BaseEntity import BaseEntity


class User(BaseEntity):
    """
    User entity representing a Discord user in the database.
    Stores global user information that persists across all guilds.
    """

    def __init__(
            self,
            id: int,
            discord_username: str,
            global_name: Optional[str] = None,
            avatar_url: Optional[str] = None,
            is_bot: bool = False,
            global_exp: int = 0,
            global_level: int = 0,
            total_currency: int = 0,
            total_messages: int = 0,
            total_reactions: int = 0,
            account_created: Union[str, datetime, None] = None,
            first_seen: Union[str, datetime, None] = None,
            last_seen: Union[str, datetime, None] = None,
            privacy_settings: Optional[str] = None,
            global_settings: Optional[str] = None
    ) -> None:
        """
        Initialize a User entity with the provided attributes.
        """
        self._id = id
        self._discord_username = discord_username
        self._global_name = global_name
        self._avatar_url = avatar_url
        self._is_bot = bool(is_bot) if is_bot is not None else False
        self._global_exp = int(global_exp) if global_exp is not None else 0
        self._global_level = int(global_level) if global_level is not None else 0
        self._total_currency = int(total_currency) if total_currency is not None else 0
        self._total_messages = int(total_messages) if total_messages is not None else 0
        self._total_reactions = int(total_reactions) if total_reactions is not None else 0
        self._account_created = account_created
        self._first_seen = first_seen
        self._last_seen = last_seen
        self._privacy_settings = privacy_settings
        self._global_settings = global_settings

    @property
    def id(self) -> int:
        """User's Discord ID"""
        return self._id

    @property
    def discord_username(self) -> str:
        """User's Discord username"""
        return self._discord_username

    @property
    def global_name(self) -> Optional[str]:
        """User's Discord global display name"""
        return self._global_name

    @property
    def avatar_url(self) -> Optional[str]:
        """User's avatar URL"""
        return self._avatar_url

    @property
    def is_bot(self) -> bool:
        """Whether the user is a bot"""
        return self._is_bot

    @property
    def global_exp(self) -> int:
        """Global experience points"""
        return self._global_exp

    @property
    def global_level(self) -> int:
        """Global level"""
        return self._global_level

    @property
    def total_currency(self) -> int:
        """Total currency across all guilds"""
        return self._total_currency

    @property
    def total_messages(self) -> int:
        """Total messages sent across all guilds"""
        return self._total_messages

    @property
    def total_reactions(self) -> int:
        """Total reactions sent across all guilds"""
        return self._total_reactions

    @property
    def account_created(self) -> Optional[str]:
        """When Discord account was created"""
        if self._account_created is None:
            return None
        elif isinstance(self._account_created, datetime):
            return self._account_created.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(self._account_created, str):
            return self._account_created if self._account_created != '0' else None
        else:
            return str(self._account_created) if self._account_created != 0 else None

    @property
    def first_seen(self) -> Optional[str]:
        """When bot first saw this user"""
        if self._first_seen is None:
            return None
        elif isinstance(self._first_seen, datetime):
            return self._first_seen.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(self._first_seen, str):
            return self._first_seen
        else:
            return str(self._first_seen)

    @property
    def last_seen(self) -> Optional[str]:
        """When bot last saw this user"""
        if self._last_seen is None:
            return None
        elif isinstance(self._last_seen, datetime):
            return self._last_seen.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(self._last_seen, str):
            return self._last_seen
        else:
            return str(self._last_seen)

    @property
    def privacy_settings(self) -> Optional[str]:
        """User's privacy settings as JSON string"""
        return self._privacy_settings

    @property
    def global_settings(self) -> Optional[str]:
        """User's global settings as JSON string"""
        return self._global_settings

    def __str__(self) -> str:
        """String representation of the user"""
        return f"User(id={self.id}, username={self.discord_username}, global_name={self.global_name})"