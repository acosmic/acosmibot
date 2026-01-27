#! /usr/bin/python3.10
"""Embed entity for embeds feature"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from Entities.BaseEntity import BaseEntity
import json


class Embed(BaseEntity):
    """
    Represents a custom Discord embed configured by users

    Attributes:
        id (int): Auto-increment primary key
        guild_id (str): Discord guild ID
        name (str): Internal name for organization
        message_text (str): Text content before embed
        embed_config (dict): Embed configuration JSON
        channel_id (str): Target channel ID
        message_id (str): Sent message ID (for editing)
        buttons (list): Button configuration JSON
        is_sent (bool): Whether embed has been sent to Discord
        created_by (str): Discord user ID who created the embed
        is_enabled (bool): Whether embed is active
        created_at (datetime): Record creation timestamp
        updated_at (datetime): Last update timestamp
    """

    def __init__(
        self,
        id: Optional[int] = None,
        guild_id: Optional[str] = None,
        name: Optional[str] = None,
        message_text: Optional[str] = None,
        embed_config: Optional[Dict[str, Any]] = None,
        channel_id: Optional[str] = None,
        message_id: Optional[str] = None,
        buttons: Optional[List[Dict[str, Any]]] = None,
        is_sent: bool = False,
        created_by: Optional[str] = None,
        is_enabled: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.guild_id = str(guild_id) if guild_id else None
        self.name = name
        self.message_text = message_text
        self.embed_config = embed_config or {}
        self.channel_id = str(channel_id) if channel_id else None
        self.message_id = str(message_id) if message_id else None
        self.buttons = buttons or []
        self.is_sent = is_sent
        self.created_by = str(created_by) if created_by else None
        self.is_enabled = is_enabled
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary for API responses"""
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'name': self.name,
            'message_text': self.message_text,
            'embed_config': self.embed_config,
            'channel_id': self.channel_id,
            'message_id': self.message_id,
            'buttons': self.buttons,
            'is_sent': self.is_sent,
            'created_by': self.created_by,
            'is_enabled': self.is_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Embed':
        """Create entity from dictionary (database row)"""
        # Convert datetime strings to datetime objects if needed
        for date_field in ['created_at', 'updated_at']:
            if data.get(date_field) and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])

        # Parse JSON embed_config if it's a string
        if data.get('embed_config') and isinstance(data['embed_config'], str):
            try:
                data['embed_config'] = json.loads(data['embed_config'])
            except json.JSONDecodeError:
                data['embed_config'] = {}

        # Parse JSON buttons if it's a string
        if data.get('buttons') and isinstance(data['buttons'], str):
            try:
                data['buttons'] = json.loads(data['buttons'])
            except json.JSONDecodeError:
                data['buttons'] = []

        return cls(**data)

    def is_draft(self) -> bool:
        """Check if embed is still a draft (not sent)"""
        return not self.is_sent

    def has_message_id(self) -> bool:
        """Check if embed has been sent and has a message ID"""
        return self.message_id is not None and self.message_id != ''

    def has_buttons(self) -> bool:
        """Check if embed has buttons configured"""
        return bool(self.buttons)

    def __repr__(self) -> str:
        return f"<Embed id={self.id} guild_id={self.guild_id} name={self.name} is_sent={self.is_sent}>"
