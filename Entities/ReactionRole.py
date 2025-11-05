#! /usr/bin/python3.10
# Entities/ReactionRole.py
from typing import Optional, Union, Any, Dict
from datetime import datetime
from Entities.BaseEntity import BaseEntity


class ReactionRole(BaseEntity):
    """
    ReactionRole entity representing a reaction role message configuration in the database.
    """

    def __init__(
            self,
            id: Optional[int] = None,
            guild_id: int = 0,
            message_id: int = 0,
            channel_id: int = 0,
            interaction_type: str = "emoji",  # emoji, button, dropdown
            text_content: Optional[str] = None,
            embed_config: Optional[str] = None,  # JSON string
            allow_removal: bool = True,
            emoji_role_mappings: Optional[str] = None,  # JSON string
            button_configs: Optional[str] = None,  # JSON string
            dropdown_config: Optional[str] = None,  # JSON string
            enabled: bool = True,
            created_at: Union[str, datetime] = None,
            updated_at: Union[str, datetime] = None
    ) -> None:
        self.id = id
        self.guild_id = guild_id
        self.message_id = message_id
        self.channel_id = channel_id
        self.interaction_type = interaction_type
        self.text_content = text_content
        self.embed_config = embed_config
        self.allow_removal = allow_removal
        self.emoji_role_mappings = emoji_role_mappings
        self.button_configs = button_configs
        self.dropdown_config = dropdown_config
        self.enabled = enabled
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def id(self) -> Optional[int]:
        return self._id if hasattr(self, '_id') else None

    @id.setter
    def id(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def guild_id(self) -> int:
        return self._guild_id

    @guild_id.setter
    def guild_id(self, value: int) -> None:
        self._guild_id = value

    @property
    def message_id(self) -> int:
        return self._message_id

    @message_id.setter
    def message_id(self, value: int) -> None:
        self._message_id = value

    @property
    def channel_id(self) -> int:
        return self._channel_id

    @channel_id.setter
    def channel_id(self, value: int) -> None:
        self._channel_id = value

    @property
    def interaction_type(self) -> str:
        return self._interaction_type

    @interaction_type.setter
    def interaction_type(self, value: str) -> None:
        if value not in ["emoji", "button", "dropdown"]:
            raise ValueError(f"Invalid interaction_type: {value}")
        self._interaction_type = value

    @property
    def text_content(self) -> Optional[str]:
        return self._text_content if hasattr(self, '_text_content') else None

    @text_content.setter
    def text_content(self, value: Optional[str]) -> None:
        self._text_content = value

    @property
    def embed_config(self) -> Optional[str]:
        return self._embed_config if hasattr(self, '_embed_config') else None

    @embed_config.setter
    def embed_config(self, value: Optional[str]) -> None:
        self._embed_config = value

    @property
    def allow_removal(self) -> bool:
        return self._allow_removal

    @allow_removal.setter
    def allow_removal(self, value: bool) -> None:
        self._allow_removal = value

    @property
    def emoji_role_mappings(self) -> Optional[str]:
        return self._emoji_role_mappings if hasattr(self, '_emoji_role_mappings') else None

    @emoji_role_mappings.setter
    def emoji_role_mappings(self, value: Optional[str]) -> None:
        self._emoji_role_mappings = value

    @property
    def button_configs(self) -> Optional[str]:
        return self._button_configs if hasattr(self, '_button_configs') else None

    @button_configs.setter
    def button_configs(self, value: Optional[str]) -> None:
        self._button_configs = value

    @property
    def dropdown_config(self) -> Optional[str]:
        return self._dropdown_config if hasattr(self, '_dropdown_config') else None

    @dropdown_config.setter
    def dropdown_config(self, value: Optional[str]) -> None:
        self._dropdown_config = value

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def created_at(self) -> Union[str, datetime]:
        return self._created_at if hasattr(self, '_created_at') else None

    @created_at.setter
    def created_at(self, value: Union[str, datetime]) -> None:
        self._created_at = value

    @property
    def updated_at(self) -> Union[str, datetime]:
        return self._updated_at if hasattr(self, '_updated_at') else None

    @updated_at.setter
    def updated_at(self, value: Union[str, datetime]) -> None:
        self._updated_at = value
