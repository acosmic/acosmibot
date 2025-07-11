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
            total_exp: int = 0,
            total_currency: int = 0,
            total_messages: int = 0,
            total_reactions: int = 0,
            account_created: Union[str, datetime] = None,
            first_seen: Union[str, datetime] = None,
            last_seen: Union[str, datetime] = None,
            privacy_settings: Optional[str] = None,
            global_settings: Optional[str] = None
    ) -> None:
        """
        Initialize a User entity with the provided attributes.

        Args:
            id (int): Discord user ID
            discord_username (str): Discord username
            global_name (Optional[str], optional): Discord global display name. Defaults to None.
            avatar_url (Optional[str], optional): User's avatar URL. Defaults to None.
            is_bot (bool, optional): Whether the user is a bot. Defaults to False.
            total_exp (int, optional): Total experience across all guilds. Defaults to 0.
            total_currency (int, optional): Total currency across all guilds. Defaults to 0.
            total_messages (int, optional): Total messages sent across all guilds. Defaults to 0.
            total_reactions (int, optional): Total reactions sent across all guilds. Defaults to 0.
            account_created (Union[str, datetime], optional): When Discord account was created. Defaults to None.
            first_seen (Union[str, datetime], optional): When bot first saw this user. Defaults to None.
            last_seen (Union[str, datetime], optional): When bot last saw this user. Defaults to None.
            privacy_settings (Optional[str], optional): JSON string of privacy settings. Defaults to None.
            global_settings (Optional[str], optional): JSON string of global settings. Defaults to None.
        """
        self.id = id
        self.discord_username = discord_username
        self.global_name = global_name
        self.avatar_url = avatar_url
        self.is_bot = is_bot
        self.total_exp = total_exp
        self.total_currency = total_currency
        self.total_messages = total_messages
        self.total_reactions = total_reactions
        self.account_created = account_created
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.privacy_settings = privacy_settings
        self.global_settings = global_settings

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
    def global_name(self) -> Optional[str]:
        """User's Discord global display name"""
        return self._global_name

    @global_name.setter
    def global_name(self, value: Optional[str]) -> None:
        """Set user's Discord global display name"""
        self._global_name = value

    @property
    def avatar_url(self) -> Optional[str]:
        """User's avatar URL"""
        return self._avatar_url

    @avatar_url.setter
    def avatar_url(self, value: Optional[str]) -> None:
        """Set user's avatar URL"""
        self._avatar_url = value

    @property
    def is_bot(self) -> bool:
        """Whether the user is a bot"""
        return self._is_bot

    @is_bot.setter
    def is_bot(self, value: bool) -> None:
        """Set whether the user is a bot"""
        self._is_bot = value

    @property
    def total_exp(self) -> int:
        """Total experience across all guilds"""
        return self._total_exp

    @total_exp.setter
    def total_exp(self, value: int) -> None:
        """Set total experience across all guilds"""
        self._total_exp = value

    @property
    def total_currency(self) -> int:
        """Total currency across all guilds"""
        return self._total_currency

    @total_currency.setter
    def total_currency(self, value: int) -> None:
        """Set total currency across all guilds"""
        self._total_currency = value

    @property
    def total_messages(self) -> int:
        """Total messages sent across all guilds"""
        return self._total_messages

    @total_messages.setter
    def total_messages(self, value: int) -> None:
        """Set total messages sent across all guilds"""
        self._total_messages = value

    @property
    def total_reactions(self) -> int:
        """Total reactions sent across all guilds"""
        return self._total_reactions

    @total_reactions.setter
    def total_reactions(self, value: int) -> None:
        """Set total reactions sent across all guilds"""
        self._total_reactions = value

    @property
    def account_created(self) -> Union[str, datetime]:
        """When Discord account was created"""
        return self._account_created

    @account_created.setter
    def account_created(self, value: Union[str, datetime]) -> None:
        """Set when Discord account was created"""
        self._account_created = value

    @property
    def first_seen(self) -> Union[str, datetime]:
        """When bot first saw this user"""
        return self._first_seen

    @first_seen.setter
    def first_seen(self, value: Union[str, datetime]) -> None:
        """Set when bot first saw this user"""
        self._first_seen = value

    @property
    def last_seen(self) -> Union[str, datetime]:
        """When bot last saw this user"""
        return self._last_seen

    @last_seen.setter
    def last_seen(self, value: Union[str, datetime]) -> None:
        """Set when bot last saw this user"""
        self._last_seen = value

    @property
    def privacy_settings(self) -> Optional[str]:
        """User's privacy settings as JSON string"""
        return self._privacy_settings

    @privacy_settings.setter
    def privacy_settings(self, value: Optional[str]) -> None:
        """Set user's privacy settings"""
        self._privacy_settings = value

    @property
    def global_settings(self) -> Optional[str]:
        """User's global settings as JSON string"""
        return self._global_settings

    @global_settings.setter
    def global_settings(self, value: Optional[str]) -> None:
        """Set user's global settings"""
        self._global_settings = value

    def __str__(self) -> str:
        """String representation of the user"""
        return f"User(id={self.id}, username={self.discord_username}, global_name={self.global_name})"