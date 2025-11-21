#! /usr/bin/python3.10
"""CustomCommand entity for premium custom commands feature"""
from datetime import datetime
from typing import Optional, Dict, Any
from Entities.BaseEntity import BaseEntity
import json


class CustomCommand(BaseEntity):
    """
    Represents a custom bot command configured by premium guilds

    Attributes:
        id (int): Auto-increment primary key
        guild_id (str): Discord guild ID
        command (str): Command word (e.g., 'welcome')
        prefix (str): Command prefix (default: '!')
        response_type (str): Response type ('text' or 'embed')
        response_text (str): Text response content
        embed_config (dict): Embed configuration JSON
        is_enabled (bool): Whether command is active
        use_count (int): Number of times command has been used
        created_by (str): Discord user ID who created the command
        created_at (datetime): Record creation timestamp
        updated_at (datetime): Last update timestamp
    """

    def __init__(
        self,
        id: Optional[int] = None,
        guild_id: Optional[str] = None,
        command: Optional[str] = None,
        prefix: str = '!',
        response_type: str = 'text',
        response_text: Optional[str] = None,
        embed_config: Optional[Dict[str, Any]] = None,
        is_enabled: bool = True,
        use_count: int = 0,
        created_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.guild_id = str(guild_id) if guild_id else None
        self.command = command
        self.prefix = prefix
        self.response_type = response_type
        self.response_text = response_text
        self.embed_config = embed_config or {}
        self.is_enabled = is_enabled
        self.use_count = use_count
        self.created_by = str(created_by) if created_by else None
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary for API responses"""
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'command': self.command,
            'prefix': self.prefix,
            'response_type': self.response_type,
            'response_text': self.response_text,
            'embed_config': self.embed_config,
            'is_enabled': self.is_enabled,
            'use_count': self.use_count,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomCommand':
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

        return cls(**data)

    def get_full_command(self) -> str:
        """Get full command with prefix"""
        return f"{self.prefix}{self.command}"

    def is_text_response(self) -> bool:
        """Check if command responds with text"""
        return self.response_type == 'text'

    def is_embed_response(self) -> bool:
        """Check if command responds with embed"""
        return self.response_type == 'embed'

    def __repr__(self) -> str:
        return f"<CustomCommand id={self.id} guild_id={self.guild_id} command={self.get_full_command()}>"
