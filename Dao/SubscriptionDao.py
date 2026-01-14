#! /usr/bin/python3.10
"""Data Access Object for Subscription entity"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from Dao.BaseDao import BaseDao
from Entities.Subscription import Subscription
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class SubscriptionDao(BaseDao[Subscription]):
    """DAO for managing guild subscriptions"""

    def __init__(self, db: Optional['Database'] = None):
        super().__init__(Subscription, "Subscriptions", db)

    def create_subscription(
        self,
        guild_id: str,
        tier: str,
        stripe_subscription_id: str,
        stripe_customer_id: str,
        current_period_start: datetime,
        current_period_end: datetime
    ) -> Optional[int]:
        """
        Create a new subscription record

        Args:
            guild_id: Discord guild ID
            tier: Subscription tier ('premium')
            stripe_subscription_id: Stripe subscription ID
            stripe_customer_id: Stripe customer ID
            current_period_start: Billing period start
            current_period_end: Billing period end

        Returns:
            Subscription ID if successful, None otherwise
        """
        query = """
            INSERT INTO Subscriptions (
                guild_id, tier, status, stripe_subscription_id, stripe_customer_id,
                current_period_start, current_period_end
            ) VALUES (%s, %s, 'active', %s, %s, %s, %s)
        """
        params = (
            str(guild_id),
            tier,
            stripe_subscription_id,
            stripe_customer_id,
            current_period_start,
            current_period_end
        )

        try:
            result = self.execute_query(query, params, commit=True)
            if result:
                logger.info(f"Created subscription for guild {guild_id}, tier: {tier}")
                return result
            return None
        except Exception as e:
            logger.error(f"Error creating subscription for guild {guild_id}: {e}")
            return None

    def get_by_guild_id(self, guild_id: str) -> Optional[Subscription]:
        """Get subscription by guild ID"""
        query = """
            SELECT id, guild_id, tier, status, stripe_subscription_id, stripe_customer_id,
                   current_period_start, current_period_end, cancel_at_period_end, cancel_at,
                   created_at, updated_at
            FROM Subscriptions WHERE guild_id = %s
        """
        results = self.execute_query(query, (str(guild_id),), return_description=True)

        if results and results[0] and len(results[0]) > 0:
            rows, description = results
            columns = [col[0] for col in description]
            row_dict = dict(zip(columns, rows[0]))
            return Subscription.from_dict(row_dict)
        return None

    def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        """Get subscription by Stripe subscription ID"""
        query = """
            SELECT id, guild_id, tier, status, stripe_subscription_id, stripe_customer_id,
                   current_period_start, current_period_end, cancel_at_period_end, cancel_at,
                   created_at, updated_at
            FROM Subscriptions WHERE stripe_subscription_id = %s
        """
        results = self.execute_query(query, (stripe_subscription_id,), return_description=True)

        if results and results[0] and len(results[0]) > 0:
            rows, description = results
            columns = [col[0] for col in description]
            row_dict = dict(zip(columns, rows[0]))
            return Subscription.from_dict(row_dict)
        return None

    def update_subscription(
        self,
        guild_id: str,
        tier: Optional[str] = None,
        status: Optional[str] = None,
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None,
        cancel_at_period_end: Optional[bool] = None,
        cancel_at: Optional[datetime] = None
    ) -> bool:
        """
        Update subscription details

        Args:
            guild_id: Discord guild ID
            tier: New tier (optional)
            status: New status (optional)
            current_period_start: New period start (optional)
            current_period_end: New period end (optional)
            cancel_at_period_end: Cancel at period end flag (optional, deprecated)
            cancel_at: Timestamp when subscription will cancel (optional)

        Returns:
            True if successful, False otherwise
        """
        updates = []
        params = []

        if tier is not None:
            updates.append("tier = %s")
            params.append(tier)

        if status is not None:
            updates.append("status = %s")
            params.append(status)

        if current_period_start is not None:
            updates.append("current_period_start = %s")
            params.append(current_period_start)

        if current_period_end is not None:
            updates.append("current_period_end = %s")
            params.append(current_period_end)

        if cancel_at_period_end is not None:
            updates.append("cancel_at_period_end = %s")
            params.append(cancel_at_period_end)

        if cancel_at is not None:
            updates.append("cancel_at = %s")
            params.append(cancel_at)

        if not updates:
            logger.warning(f"No updates provided for subscription {guild_id}")
            return False

        updates.append("updated_at = NOW()")
        params.append(str(guild_id))

        query = f"UPDATE Subscriptions SET {', '.join(updates)} WHERE guild_id = %s"

        try:
            self.execute_query(query, tuple(params), commit=True)
            logger.info(f"Updated subscription for guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating subscription for guild {guild_id}: {e}")
            return False

    def update_by_stripe_subscription_id(
        self,
        stripe_subscription_id: str,
        status: Optional[str] = None,
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None,
        cancel_at_period_end: Optional[bool] = None,
        cancel_at: Optional[datetime] = None
    ) -> bool:
        """
        Update subscription by Stripe subscription ID (used in webhooks)

        Returns:
            True if successful, False otherwise
        """
        updates = []
        params = []

        if status is not None:
            updates.append("status = %s")
            params.append(status)

        if current_period_start is not None:
            updates.append("current_period_start = %s")
            params.append(current_period_start)

        if current_period_end is not None:
            updates.append("current_period_end = %s")
            params.append(current_period_end)

        if cancel_at_period_end is not None:
            updates.append("cancel_at_period_end = %s")
            params.append(cancel_at_period_end)

        if cancel_at is not None:
            updates.append("cancel_at = %s")
            params.append(cancel_at)

        if not updates:
            return False

        updates.append("updated_at = NOW()")
        params.append(stripe_subscription_id)

        query = f"UPDATE Subscriptions SET {', '.join(updates)} WHERE stripe_subscription_id = %s"

        try:
            logger.info(f"Executing update query: {query} with params: {tuple(params)}")
            self.execute_query(query, tuple(params), commit=True)
            logger.info(f"Updated subscription {stripe_subscription_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating subscription {stripe_subscription_id}: {e}")
            return False

    def cancel_subscription(self, guild_id: str) -> bool:
        """Mark subscription as canceled"""
        return self.update_subscription(guild_id, status='canceled', cancel_at_period_end=True)

    def get_all_active_subscriptions(self) -> List[Subscription]:
        """Get all active premium subscriptions"""
        query = """
            SELECT id, guild_id, tier, status, stripe_subscription_id, stripe_customer_id,
                   current_period_start, current_period_end, cancel_at_period_end, cancel_at,
                   created_at, updated_at
            FROM Subscriptions WHERE status = 'active' AND tier != 'free'
        """
        results = self.execute_query(query, fetch_all=True)

        if results:
            return [Subscription.from_dict(row) for row in results]
        return []

    def get_expiring_subscriptions(self, days_before: int = 7) -> List[Subscription]:
        """Get subscriptions expiring in N days"""
        query = """
            SELECT id, guild_id, tier, status, stripe_subscription_id, stripe_customer_id,
                   current_period_start, current_period_end, cancel_at_period_end, cancel_at,
                   created_at, updated_at
            FROM Subscriptions
            WHERE status = 'active'
            AND tier != 'free'
            AND current_period_end BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL %s DAY)
        """
        results = self.execute_query(query, (days_before,), fetch_all=True)

        if results:
            return [Subscription.from_dict(row) for row in results]
        return []

    def get_past_due_subscriptions(self) -> List[Subscription]:
        """Get all subscriptions with past_due status"""
        query = """
            SELECT id, guild_id, tier, status, stripe_subscription_id, stripe_customer_id,
                   current_period_start, current_period_end, cancel_at_period_end, cancel_at,
                   created_at, updated_at
            FROM Subscriptions WHERE status = 'past_due'
        """
        results = self.execute_query(query, fetch_all=True)

        if results:
            return [Subscription.from_dict(row) for row in results]
        return []

    def delete_subscription(self, guild_id: str) -> bool:
        """Delete subscription record (use with caution)"""
        query = "DELETE FROM Subscriptions WHERE guild_id = %s"

        try:
            self.execute_query(query, (str(guild_id),), commit=True)
            logger.info(f"Deleted subscription for guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting subscription for guild {guild_id}: {e}")
            return False

    def get_subscription_stats(self) -> Dict[str, int]:
        """Get subscription statistics"""
        query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN tier = 'premium' AND status = 'active' THEN 1 ELSE 0 END) as active_premium,
                SUM(CASE WHEN tier = 'free' THEN 1 ELSE 0 END) as free_tier,
                SUM(CASE WHEN status = 'past_due' THEN 1 ELSE 0 END) as past_due,
                SUM(CASE WHEN status = 'canceled' THEN 1 ELSE 0 END) as canceled
            FROM Subscriptions
        """
        result = self.execute_query(query, fetch_one=True)

        if result:
            return {
                'total': result['total'] or 0,
                'active_premium': result['active_premium'] or 0,
                'free_tier': result['free_tier'] or 0,
                'past_due': result['past_due'] or 0,
                'canceled': result['canceled'] or 0
            }
        return {}
