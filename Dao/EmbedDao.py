#! /usr/bin/python3.10
"""Data Access Object for Embed entity"""
from typing import Optional, List, Dict, Any
import json
from Dao.BaseDao import BaseDao
from Entities.Embed import Embed
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class EmbedDao(BaseDao):
    """DAO for managing embeds"""

    def __init__(self):
        super().__init__(table_name="Embeds", entity_class=Embed)
        self.table_name = "Embeds"

    def create_embed(
        self,
        guild_id: str,
        name: str,
        created_by: str,
        embed_config: Dict[str, Any],
        message_text: Optional[str] = None,
        channel_id: Optional[str] = None,
        buttons: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[int]:
        """
        Create a new embed

        Args:
            guild_id: Discord guild ID
            name: Internal name for organization
            created_by: Discord user ID who created the embed
            embed_config: Embed configuration dictionary
            message_text: Text content before embed
            channel_id: Target channel ID
            buttons: Button configuration list

        Returns:
            Embed ID if successful, None otherwise
        """
        # Serialize JSON fields
        embed_json = json.dumps(embed_config)
        buttons_json = json.dumps(buttons) if buttons else None

        query = """
            INSERT INTO Embeds (
                guild_id, name, message_text, embed_config,
                channel_id, buttons, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            str(guild_id),
            name,
            message_text,
            embed_json,
            str(channel_id) if channel_id else None,
            buttons_json,
            str(created_by)
        )

        try:
            result = self.execute_write(query, params)
            if result:
                logger.info(f"Created embed '{name}' for guild {guild_id}")
                return result
            return None
        except Exception as e:
            logger.error(f"Error creating embed for guild {guild_id}: {e}")
            return None

    def get_embed(self, embed_id: int) -> Optional[Embed]:
        """Get embed by ID"""
        query = """
            SELECT id, guild_id, name, message_text, embed_config,
                   channel_id, message_id, buttons, is_sent, created_by,
                   is_enabled, created_at, updated_at
            FROM Embeds WHERE id = %s
        """
        results, description = self.execute_query(query, (embed_id,), return_description=True)

        if results and len(results) > 0 and description:
            columns = [column[0] for column in description]
            entity_dict = dict(zip(columns, results[0]))
            return Embed.from_dict(entity_dict)
        return None

    def get_guild_embeds(
        self,
        guild_id: str,
        enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all embeds for a guild

        Args:
            guild_id: Discord guild ID
            enabled_only: If True, only return enabled embeds

        Returns:
            List of embed dictionaries
        """
        query = """
            SELECT id, guild_id, name, message_text, embed_config,
                   channel_id, message_id, buttons, is_sent, created_by,
                   is_enabled, created_at, updated_at
            FROM Embeds WHERE guild_id = %s
        """
        params = [str(guild_id)]

        if enabled_only:
            query += " AND is_enabled = TRUE"

        query += " ORDER BY created_at DESC"

        results, description = self.execute_query(query, tuple(params), return_description=True)

        if results and description:
            columns = [column[0] for column in description]
            return [Embed.from_dict(dict(zip(columns, row))).to_dict() for row in results]
        return []

    def update_embed(
        self,
        embed_id: int,
        guild_id: str,
        name: Optional[str] = None,
        message_text: Optional[str] = None,
        embed_config: Optional[Dict[str, Any]] = None,
        channel_id: Optional[str] = None,
        buttons: Optional[List[Dict[str, Any]]] = None,
        is_enabled: Optional[bool] = None
    ) -> bool:
        """
        Update embed

        Args:
            embed_id: Embed ID to update
            guild_id: Guild ID (for security check)
            name: New name (optional)
            message_text: New message text (optional)
            embed_config: New embed config (optional)
            channel_id: New channel ID (optional)
            buttons: New buttons (optional)
            is_enabled: New enabled status (optional)

        Returns:
            True if successful, False otherwise
        """
        updates = []
        params = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)

        if message_text is not None:
            updates.append("message_text = %s")
            params.append(message_text)

        if embed_config is not None:
            updates.append("embed_config = %s")
            params.append(json.dumps(embed_config))

        if channel_id is not None:
            updates.append("channel_id = %s")
            params.append(str(channel_id))

        if buttons is not None:
            updates.append("buttons = %s")
            params.append(json.dumps(buttons))

        if is_enabled is not None:
            updates.append("is_enabled = %s")
            params.append(is_enabled)

        if not updates:
            logger.warning(f"No updates provided for embed {embed_id}")
            return False

        updates.append("updated_at = NOW()")
        params.extend([embed_id, str(guild_id)])

        query = f"UPDATE Embeds SET {', '.join(updates)} WHERE id = %s AND guild_id = %s"

        try:
            result = self.execute_write(query, tuple(params))
            logger.info(f"Updated embed {embed_id}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error updating embed {embed_id}: {e}")
            return False

    def update_message_id(self, embed_id: int, message_id: str) -> bool:
        """
        Update the Discord message ID for an embed

        Args:
            embed_id: Embed ID
            message_id: Discord message ID

        Returns:
            True if successful, False otherwise
        """
        query = "UPDATE Embeds SET message_id = %s, updated_at = NOW() WHERE id = %s"

        try:
            result = self.execute_write(query, (str(message_id), embed_id))
            logger.info(f"Updated message ID for embed {embed_id}: {message_id}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error updating message ID for embed {embed_id}: {e}")
            return False

    def mark_as_sent(self, embed_id: int) -> bool:
        """
        Mark embed as sent

        Args:
            embed_id: Embed ID

        Returns:
            True if successful, False otherwise
        """
        query = "UPDATE Embeds SET is_sent = TRUE, updated_at = NOW() WHERE id = %s"

        try:
            result = self.execute_write(query, (embed_id,))
            logger.info(f"Marked embed {embed_id} as sent")
            return bool(result)
        except Exception as e:
            logger.error(f"Error marking embed {embed_id} as sent: {e}")
            return False

    def delete_embed(self, embed_id: int, guild_id: str) -> bool:
        """Delete embed"""
        query = "DELETE FROM Embeds WHERE id = %s AND guild_id = %s"

        try:
            result = self.execute_write(query, (embed_id, str(guild_id)))
            logger.info(f"Deleted embed {embed_id}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting embed {embed_id}: {e}")
            return False

    def count_guild_embeds(self, guild_id: str) -> int:
        """Count total embeds for a guild"""
        query = "SELECT COUNT(*) as count FROM Embeds WHERE guild_id = %s"
        results = self.execute_query(query, (str(guild_id),))

        if results and len(results) > 0:
            result = results[0]
            # Handle both dict and tuple results
            if isinstance(result, dict):
                return result['count'] or 0
            elif isinstance(result, tuple):
                return result[0] or 0
        return 0

    def get_sent_embeds(self, guild_id: str) -> List[Dict[str, Any]]:
        """Get all sent embeds for a guild"""
        query = """
            SELECT id, guild_id, name, message_text, embed_config,
                   channel_id, message_id, buttons, is_sent, created_by,
                   is_enabled, created_at, updated_at
            FROM Embeds
            WHERE guild_id = %s AND is_sent = TRUE
            ORDER BY created_at DESC
        """
        results, description = self.execute_query(query, (str(guild_id),), return_description=True)

        if results and description:
            columns = [column[0] for column in description]
            return [Embed.from_dict(dict(zip(columns, row))).to_dict() for row in results]
        return []

    def get_draft_embeds(self, guild_id: str) -> List[Dict[str, Any]]:
        """Get all draft (unsent) embeds for a guild"""
        query = """
            SELECT id, guild_id, name, message_text, embed_config,
                   channel_id, message_id, buttons, is_sent, created_by,
                   is_enabled, created_at, updated_at
            FROM Embeds
            WHERE guild_id = %s AND is_sent = FALSE
            ORDER BY created_at DESC
        """
        results, description = self.execute_query(query, (str(guild_id),), return_description=True)

        if results and description:
            columns = [column[0] for column in description]
            return [Embed.from_dict(dict(zip(columns, row))).to_dict() for row in results]
        return []

    def disable_embed(self, embed_id: int, guild_id: str) -> bool:
        """Disable an embed"""
        return self.update_embed(embed_id, guild_id, is_enabled=False)

    def enable_embed(self, embed_id: int, guild_id: str) -> bool:
        """Enable an embed"""
        return self.update_embed(embed_id, guild_id, is_enabled=True)
