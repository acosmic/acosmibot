#! /usr/bin/python3.10
"""AIUsage entity for tracking AI usage and enforcing limits"""
from datetime import datetime
from typing import Optional, Dict, Any
from Entities.BaseEntity import BaseEntity


class AIUsage(BaseEntity):
    """
    Represents a single AI usage event for rate limiting and cost tracking

    Attributes:
        id (int): Auto-increment primary key
        guild_id (str): Discord guild ID
        user_id (str): Discord user ID
        usage_type (str): Type of usage ('chat', 'image_generation', 'image_analysis')
        model (str): AI model used (e.g., 'gpt-4', 'dall-e-3')
        tokens_used (int): Number of tokens consumed
        cost_usd (float): Cost in USD
        timestamp (datetime): When the usage occurred
    """

    def __init__(
        self,
        id: Optional[int] = None,
        guild_id: Optional[str] = None,
        user_id: Optional[str] = None,
        usage_type: str = 'chat',
        model: Optional[str] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        timestamp: Optional[datetime] = None
    ):
        self.id = id
        self.guild_id = str(guild_id) if guild_id else None
        self.user_id = str(user_id) if user_id else None
        self.usage_type = usage_type
        self.model = model
        self.tokens_used = tokens_used
        self.cost_usd = cost_usd
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary for API responses"""
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'user_id': self.user_id,
            'usage_type': self.usage_type,
            'model': self.model,
            'tokens_used': self.tokens_used,
            'cost_usd': float(self.cost_usd),
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIUsage':
        """Create entity from dictionary (database row)"""
        # Convert datetime string to datetime object if needed
        if data.get('timestamp') and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])

        return cls(**data)

    def is_chat_usage(self) -> bool:
        """Check if this is a chat usage event"""
        return self.usage_type == 'chat'

    def is_image_generation(self) -> bool:
        """Check if this is an image generation event"""
        return self.usage_type == 'image_generation'

    def is_image_analysis(self) -> bool:
        """Check if this is an image analysis event"""
        return self.usage_type == 'image_analysis'

    def __repr__(self) -> str:
        return f"<AIUsage id={self.id} guild_id={self.guild_id} type={self.usage_type} model={self.model}>"
