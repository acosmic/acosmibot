#! /usr/bin/python3.10
"""
AIImageDao - Data Access Object for AI Images

Handles database operations for AI-generated and analyzed images.
"""

from Dao.BaseDao import BaseDao
from Entities.AIImage import AIImage
from logger import AppLogger
from typing import List, Optional, Dict
from datetime import datetime, timedelta

logger = AppLogger(__name__).get_logger()


class AIImageDao(BaseDao):
    """DAO for AI image operations"""

    def __init__(self):
        super().__init__(table_name='AIImages', entity_class=AIImage)

    def add_image(self, ai_image: AIImage) -> Optional[int]:
        """
        Add a new AI image record to the database.

        Args:
            ai_image: AIImage entity to add

        Returns:
            int: ID of the created record, or None if failed
        """
        connection = None
        cursor = None

        try:
            sql = """
                INSERT INTO AIImages (
                    guild_id, user_id, type, prompt, image_url,
                    revised_prompt, analysis_result, model, size, quality, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                ai_image.guild_id,
                ai_image.user_id,
                ai_image.type,
                ai_image.prompt,
                ai_image.image_url,
                ai_image.revised_prompt,
                ai_image.analysis_result,
                ai_image.model,
                ai_image.size,
                ai_image.quality,
                ai_image.created_at
            )

            # Get connection for INSERT
            connection = self.db._get_pooled_connection(retries=3, retry_delay=0.05)
            if not connection:
                logger.error("Failed to get database connection")
                return None

            cursor = connection.cursor()
            cursor.execute(sql, params)
            connection.commit()

            last_id = cursor.lastrowid
            return last_id

        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            logger.error(f"Error adding AI image: {e}", exc_info=True)
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def get_guild_images(
        self,
        guild_id: str,
        type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get AI images for a guild.

        Args:
            guild_id: Guild ID
            type: Filter by type ('generation' or 'analysis'), None for all
            limit: Maximum number of records to return

        Returns:
            List of AI image dictionaries
        """
        try:
            if type:
                sql = """
                    SELECT * FROM AIImages
                    WHERE guild_id = %s AND type = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params = (guild_id, type, limit)
            else:
                sql = """
                    SELECT * FROM AIImages
                    WHERE guild_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params = (guild_id, limit)

            results = self.execute_query(sql, params)
            return [self._row_to_dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting guild images: {e}", exc_info=True)
            return []

    def get_user_images(
        self,
        user_id: str,
        guild_id: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get AI images for a user.

        Args:
            user_id: User ID
            guild_id: Optional guild ID filter
            type: Filter by type ('generation' or 'analysis'), None for all
            limit: Maximum number of records to return

        Returns:
            List of AI image dictionaries
        """
        try:
            conditions = ["user_id = %s"]
            params = [user_id]

            if guild_id:
                conditions.append("guild_id = %s")
                params.append(guild_id)

            if type:
                conditions.append("type = %s")
                params.append(type)

            params.append(limit)

            sql = f"""
                SELECT * FROM AIImages
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
                LIMIT %s
            """

            results = self.execute_query(sql, tuple(params))
            return [self._row_to_dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting user images: {e}", exc_info=True)
            return []

    def count_monthly_images(
        self,
        guild_id: str,
        type: str = 'generation'
    ) -> int:
        """
        Count images created this month for a guild.

        Args:
            guild_id: Guild ID
            type: Image type ('generation' or 'analysis')

        Returns:
            Number of images this month
        """
        try:
            # Get first day of current month
            now = datetime.now()
            first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            sql = """
                SELECT COUNT(*) as count
                FROM AIImages
                WHERE guild_id = %s
                AND type = %s
                AND created_at >= %s
            """
            params = (guild_id, type, first_day)

            results = self.execute_query(sql, params)
            if results and len(results) > 0:
                result = results[0]
                # Handle both dict and tuple results
                if isinstance(result, dict):
                    return result['count']
                elif isinstance(result, tuple):
                    return result[0]
            return 0

        except Exception as e:
            logger.error(f"Error counting monthly images: {e}", exc_info=True)
            return 0

    def get_usage_stats(self, guild_id: str) -> Dict:
        """
        Get usage statistics for a guild.

        Args:
            guild_id: Guild ID

        Returns:
            Dict with usage statistics
        """
        try:
            now = datetime.now()
            first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            sql = """
                SELECT
                    type,
                    COUNT(*) as count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM AIImages
                WHERE guild_id = %s AND created_at >= %s
                GROUP BY type
            """
            params = (guild_id, first_day)

            results = self.execute_query(sql, params)

            stats = {
                'generation': {'count': 0, 'unique_users': 0},
                'analysis': {'count': 0, 'unique_users': 0},
                'total': 0,
                'period_start': first_day.isoformat()
            }

            if results:
                for row in results:
                    type_name = row['type']
                    stats[type_name] = {
                        'count': row['count'],
                        'unique_users': row['unique_users']
                    }
                    stats['total'] += row['count']

            return stats

        except Exception as e:
            logger.error(f"Error getting usage stats: {e}", exc_info=True)
            return {
                'generation': {'count': 0, 'unique_users': 0},
                'analysis': {'count': 0, 'unique_users': 0},
                'total': 0
            }

    def _row_to_dict(self, row: tuple) -> Dict:
        """Convert database row to dictionary"""
        if isinstance(row, dict):
            return row

        # Assuming row is a tuple from cursor.fetchall()
        # This matches the column order from SELECT * queries
        return {
            'id': row[0],
            'guild_id': row[1],
            'user_id': row[2],
            'type': row[3],
            'prompt': row[4],
            'image_url': row[5],
            'revised_prompt': row[6],
            'analysis_result': row[7],
            'model': row[8],
            'size': row[9],
            'quality': row[10],
            'created_at': row[11].isoformat() if row[11] else None
        }
