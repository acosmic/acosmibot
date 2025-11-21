#! /usr/bin/python3.10
"""Data Access Object for AIUsage entity"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from Dao.BaseDao import BaseDao
from Entities.AIUsage import AIUsage
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class AIUsageDao(BaseDao):
    """DAO for tracking and querying AI usage"""

    def __init__(self):
        super().__init__()
        self.table_name = "AIUsage"

    def record_usage(
        self,
        guild_id: str,
        user_id: str,
        usage_type: str,
        model: str,
        tokens_used: int = 0,
        cost_usd: float = 0.0
    ) -> Optional[int]:
        """
        Record an AI usage event

        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            usage_type: 'chat', 'image_generation', or 'image_analysis'
            model: Model used (e.g., 'gpt-4', 'dall-e-3')
            tokens_used: Number of tokens consumed
            cost_usd: Cost in USD

        Returns:
            Usage record ID if successful, None otherwise
        """
        query = """
            INSERT INTO AIUsage (
                guild_id, user_id, usage_type, model, tokens_used, cost_usd
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (str(guild_id), str(user_id), usage_type, model, tokens_used, cost_usd)

        try:
            result = self.execute_query(query, params, fetch=False)
            if result:
                logger.debug(f"Recorded AI usage for guild {guild_id}, type: {usage_type}, model: {model}")
                return result
            return None
        except Exception as e:
            logger.error(f"Error recording AI usage for guild {guild_id}: {e}")
            return None

    def get_daily_usage_count(
        self,
        guild_id: str,
        usage_type: str = 'chat'
    ) -> int:
        """
        Get count of AI usages today for a guild

        Args:
            guild_id: Discord guild ID
            usage_type: Type of usage to count (default: 'chat')

        Returns:
            Number of usages today
        """
        query = """
            SELECT COUNT(*) as count
            FROM AIUsage
            WHERE guild_id = %s
            AND usage_type = %s
            AND DATE(timestamp) = CURDATE()
        """
        result = self.execute_query(query, (str(guild_id), usage_type), fetch_one=True)

        if result:
            return result['count'] or 0
        return 0

    def get_monthly_usage(
        self,
        guild_id: str,
        usage_type: str
    ) -> int:
        """
        Get count of AI usages this month for a guild

        Args:
            guild_id: Discord guild ID
            usage_type: Type of usage to count

        Returns:
            Number of usages this month
        """
        query = """
            SELECT COUNT(*) as count
            FROM AIUsage
            WHERE guild_id = %s
            AND usage_type = %s
            AND YEAR(timestamp) = YEAR(CURDATE())
            AND MONTH(timestamp) = MONTH(CURDATE())
        """
        result = self.execute_query(query, (str(guild_id), usage_type), fetch_one=True)

        if result:
            return result['count'] or 0
        return 0

    def get_user_daily_usage(
        self,
        guild_id: str,
        user_id: str,
        usage_type: str = 'chat'
    ) -> int:
        """Get daily usage count for a specific user"""
        query = """
            SELECT COUNT(*) as count
            FROM AIUsage
            WHERE guild_id = %s
            AND user_id = %s
            AND usage_type = %s
            AND DATE(timestamp) = CURDATE()
        """
        result = self.execute_query(query, (str(guild_id), str(user_id), usage_type), fetch_one=True)

        if result:
            return result['count'] or 0
        return 0

    def get_usage_stats(
        self,
        guild_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a guild over the last N days

        Returns:
            Dictionary with usage stats by type
        """
        query = """
            SELECT
                usage_type,
                COUNT(*) as count,
                SUM(tokens_used) as total_tokens,
                SUM(cost_usd) as total_cost
            FROM AIUsage
            WHERE guild_id = %s
            AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY usage_type
        """
        results = self.execute_query(query, (str(guild_id), days), fetch_all=True)

        stats = {}
        if results:
            for row in results:
                stats[row['usage_type']] = {
                    'count': row['count'] or 0,
                    'total_tokens': row['total_tokens'] or 0,
                    'total_cost': float(row['total_cost'] or 0)
                }

        return stats

    def get_model_usage(
        self,
        guild_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get usage breakdown by model"""
        query = """
            SELECT
                model,
                COUNT(*) as usage_count,
                SUM(tokens_used) as total_tokens,
                SUM(cost_usd) as total_cost
            FROM AIUsage
            WHERE guild_id = %s
            AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY model
            ORDER BY usage_count DESC
        """
        results = self.execute_query(query, (str(guild_id), days), fetch_all=True)

        if results:
            return [
                {
                    'model': row['model'],
                    'usage_count': row['usage_count'] or 0,
                    'total_tokens': row['total_tokens'] or 0,
                    'total_cost': float(row['total_cost'] or 0)
                }
                for row in results
            ]
        return []

    def record_image_generation(
        self,
        guild_id: str,
        user_id: str,
        prompt: str,
        image_url: str,
        revised_prompt: Optional[str] = None,
        size: str = '1024x1024'
    ) -> Optional[int]:
        """
        Record an image generation event

        This method records both in AIUsage and AIImages tables

        Returns:
            AIImages record ID if successful, None otherwise
        """
        # Record in AIUsage table for rate limiting
        self.record_usage(
            guild_id=guild_id,
            user_id=user_id,
            usage_type='image_generation',
            model='dall-e-3',
            tokens_used=0,  # DALL-E doesn't use tokens
            cost_usd=0.04  # Approximate cost per image
        )

        # Record in AIImages table
        query = """
            INSERT INTO AIImages (
                guild_id, user_id, prompt, image_url, revised_prompt, size
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (str(guild_id), str(user_id), prompt, image_url, revised_prompt, size)

        try:
            result = self.execute_query(query, params, fetch=False)
            if result:
                logger.info(f"Recorded image generation for guild {guild_id}")
                return result
            return None
        except Exception as e:
            logger.error(f"Error recording image generation for guild {guild_id}: {e}")
            return None

    def get_image_history(
        self,
        guild_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get image generation history for a guild"""
        query = """
            SELECT * FROM AIImages
            WHERE guild_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        results = self.execute_query(query, (str(guild_id), limit), fetch_all=True)

        if results:
            return [dict(row) for row in results]
        return []

    def delete_old_usage_records(self, days: int = 90) -> int:
        """Delete usage records older than N days (maintenance task)"""
        query = "DELETE FROM AIUsage WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)"

        try:
            result = self.execute_query(query, (days,), fetch=False)
            logger.info(f"Deleted old AI usage records (older than {days} days)")
            return result or 0
        except Exception as e:
            logger.error(f"Error deleting old AI usage records: {e}")
            return 0

    def get_top_ai_users(
        self,
        guild_id: str,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get top AI users in a guild"""
        query = """
            SELECT
                user_id,
                COUNT(*) as total_usage,
                SUM(CASE WHEN usage_type = 'chat' THEN 1 ELSE 0 END) as chat_usage,
                SUM(CASE WHEN usage_type = 'image_generation' THEN 1 ELSE 0 END) as image_usage
            FROM AIUsage
            WHERE guild_id = %s
            AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY user_id
            ORDER BY total_usage DESC
            LIMIT %s
        """
        results = self.execute_query(query, (str(guild_id), days, limit), fetch_all=True)

        if results:
            return [dict(row) for row in results]
        return []
