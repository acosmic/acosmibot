from typing import Optional, Union, Any
from datetime import datetime
from decimal import Decimal
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
            bank_balance: int = 0,
            daily_transfer_amount: int = 0,
            last_transfer_reset: Union[str, datetime, None] = None,
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

        # Convert Decimal to int for numeric fields
        self._global_exp = self._convert_to_int(global_exp)
        self._global_level = self._convert_to_int(global_level)
        self._total_currency = self._convert_to_int(total_currency)
        self._bank_balance = self._convert_to_int(bank_balance)
        self._daily_transfer_amount = self._convert_to_int(daily_transfer_amount)
        self._total_messages = self._convert_to_int(total_messages)
        self._total_reactions = self._convert_to_int(total_reactions)

        self._account_created = account_created
        self._first_seen = first_seen
        self._last_seen = last_seen
        self._last_transfer_reset = last_transfer_reset
        self._privacy_settings = privacy_settings
        self._global_settings = global_settings

    def _convert_to_int(self, value) -> int:
        """Convert Decimal or other numeric types to int safely"""
        if value is None:
            return 0
        if isinstance(value, Decimal):
            return int(value)
        return int(value) if value is not None else 0

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

    @global_exp.setter
    def global_exp(self, value):
        """Set global experience points, ensuring it's an int"""
        self._global_exp = self._convert_to_int(value)

    @property
    def global_level(self) -> int:
        """Global level"""
        return self._global_level

    @global_level.setter
    def global_level(self, value):
        """Set global level, ensuring it's an int"""
        self._global_level = self._convert_to_int(value)

    @property
    def total_currency(self) -> int:
        """Total currency across all guilds"""
        return self._total_currency

    @total_currency.setter
    def total_currency(self, value):
        """Set total currency, ensuring it's an int"""
        self._total_currency = self._convert_to_int(value)

    @property
    def bank_balance(self) -> int:
        """Currency stored in personal bank"""
        return self._bank_balance

    @bank_balance.setter
    def bank_balance(self, value):
        """Set bank balance, ensuring it's an int"""
        self._bank_balance = self._convert_to_int(value)

    @property
    def daily_transfer_amount(self) -> int:
        """Amount transferred today (for daily limit tracking)"""
        return self._daily_transfer_amount

    @daily_transfer_amount.setter
    def daily_transfer_amount(self, value):
        """Set daily transfer amount, ensuring it's an int"""
        self._daily_transfer_amount = self._convert_to_int(value)

    @property
    def last_transfer_reset(self) -> Union[str, datetime, None]:
        """Last date when daily transfer amount was reset"""
        return self._last_transfer_reset

    @last_transfer_reset.setter
    def last_transfer_reset(self, value):
        """Set last transfer reset date"""
        self._last_transfer_reset = value

    @property
    def total_messages(self) -> int:
        """Total messages sent across all guilds"""
        return self._total_messages

    @total_messages.setter
    def total_messages(self, value):
        """Set total messages, ensuring it's an int"""
        self._total_messages = self._convert_to_int(value)

    @property
    def total_reactions(self) -> int:
        """Total reactions sent across all guilds"""
        return self._total_reactions

    @total_reactions.setter
    def total_reactions(self, value):
        """Set total reactions, ensuring it's an int"""
        self._total_reactions = self._convert_to_int(value)

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

    @last_seen.setter
    def last_seen(self, value):
        """Set last seen timestamp"""
        self._last_seen = value

    @property
    def privacy_settings(self) -> Optional[str]:
        """User's privacy models as JSON string"""
        return self._privacy_settings

    @property
    def global_settings(self) -> Optional[str]:
        """User's global models as JSON string"""
        return self._global_settings

    def __str__(self) -> str:
        """String representation of the user"""
        return f"User(id={self.id}, username={self.discord_username}, global_name={self.global_name})"