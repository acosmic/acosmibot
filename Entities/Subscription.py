#! /usr/bin/python3.10
"""Subscription entity for premium subscription tracking"""
from datetime import datetime
from typing import Optional, Dict, Any
from Entities.BaseEntity import BaseEntity


class Subscription(BaseEntity):
    """
    Represents a guild's premium subscription

    Attributes:
        id (int): Auto-increment primary key
        guild_id (str): Discord guild ID
        tier (str): Subscription tier ('free', 'premium', 'premium_plus_ai')
        status (str): Subscription status ('active', 'past_due', 'canceled', 'expired')
        current_period_start (datetime): Start of current billing period
        current_period_end (datetime): End of current billing period
        stripe_subscription_id (str): Stripe subscription ID
        stripe_customer_id (str): Stripe customer ID
        cancel_at_period_end (bool): Whether subscription cancels at period end (deprecated, use cancel_at)
        cancel_at (datetime): Timestamp when subscription will be canceled (None if not scheduled)
        created_at (datetime): Record creation timestamp
        updated_at (datetime): Last update timestamp
    """

    def __init__(
        self,
        id: Optional[int] = None,
        guild_id: Optional[str] = None,
        tier: str = 'free',
        status: str = 'active',
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None,
        stripe_subscription_id: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
        cancel_at_period_end: bool = False,
        cancel_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.guild_id = str(guild_id) if guild_id else None
        self.tier = tier
        self.status = status
        self.current_period_start = current_period_start
        self.current_period_end = current_period_end
        self.stripe_subscription_id = stripe_subscription_id
        self.stripe_customer_id = stripe_customer_id
        self.cancel_at_period_end = cancel_at_period_end
        self.cancel_at = cancel_at
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary for API responses"""
        return {
            'id': self.id,
            'guild_id': self.guild_id,
            'tier': self.tier,
            'status': self.status,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'stripe_subscription_id': self.stripe_subscription_id,
            'stripe_customer_id': self.stripe_customer_id,
            'cancel_at_period_end': self.cancel_at_period_end,
            'cancel_at': self.cancel_at.isoformat() if self.cancel_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subscription':
        """Create entity from dictionary (database row)"""
        # Convert datetime strings to datetime objects if needed
        for date_field in ['current_period_start', 'current_period_end', 'cancel_at', 'created_at', 'updated_at']:
            if data.get(date_field) and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])

        return cls(**data)

    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return self.status == 'active' and self.tier != 'free'

    def is_past_due(self) -> bool:
        """Check if subscription payment is past due"""
        return self.status == 'past_due'

    def is_canceled(self) -> bool:
        """Check if subscription is canceled"""
        return self.status == 'canceled'

    def has_premium(self) -> bool:
        """Check if subscription has premium access (premium or premium_plus_ai)"""
        return self.tier in ['premium', 'premium_plus_ai'] and self.status in ['active', 'past_due']

    def has_ai_access(self) -> bool:
        """Check if subscription has enhanced AI access (premium_plus_ai only)"""
        return self.tier == 'premium_plus_ai' and self.status in ['active', 'past_due']

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} guild_id={self.guild_id} tier={self.tier} status={self.status}>"
