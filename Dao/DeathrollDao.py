from typing import Optional, List
from database import Database
from Dao.BaseDao import BaseDao
from Entities.DeathrollEvent import DeathrollEvent
import logging


class DeathrollDao(BaseDao[DeathrollEvent]):
    """
    Data Access Object for DeathrollEvent entities.
    Updated for multi-guild support with optional persistent storage.
    Note: With the new design, persistent storage is optional since games are self-contained.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the DeathrollDao with connection parameters.

        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(DeathrollEvent, "DeathrollEvents", db)

        # Create the table if it doesn't exist
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> None:
        """
        Create the DeathrollEvents table if it doesn't exist.
        Updated to include guild_id for multi-guild support.
        """
        create_table_sql = '''
                           CREATE TABLE IF NOT EXISTS DeathrollEvents \
                           ( \
                               id \
                               INT \
                               AUTO_INCREMENT \
                               PRIMARY \
                               KEY, \
                               guild_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               initiator_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               acceptor_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               bet \
                               INT \
                               NOT \
                               NULL, \
                               message_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               current_roll \
                               INT \
                               NOT \
                               NULL, \
                               current_player_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               is_finished \
                               BOOLEAN \
                               NOT \
                               NULL \
                               DEFAULT \
                               FALSE, \
                               created_at \
                               TIMESTAMP \
                               DEFAULT \
                               CURRENT_TIMESTAMP, \
                               updated_at \
                               TIMESTAMP \
                               DEFAULT \
                               CURRENT_TIMESTAMP \
                               ON \
                               UPDATE \
                               CURRENT_TIMESTAMP, \
                               INDEX \
                               idx_guild_active \
                           ( \
                               guild_id, \
                               is_finished \
                           ),
                               INDEX idx_message \
                           ( \
                               message_id \
                           ),
                               INDEX idx_users \
                           ( \
                               initiator_id, \
                               acceptor_id \
                           )
                               ) \
                           '''
        self.create_table_if_not_exists(create_table_sql)

    def add_new_event(self, deathroll_event: DeathrollEvent, guild_id: int) -> bool:
        """
        Add a new deathroll event to the database.

        Args:
            deathroll_event (DeathrollEvent): Deathroll event to add
            guild_id (int): Guild ID where the event is taking place

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
              INSERT INTO DeathrollEvents (guild_id, initiator_id, acceptor_id, bet, message_id, current_roll, \
                                           current_player_id, is_finished)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s) \
              """
        values = (
            guild_id,
            deathroll_event.initiator,
            deathroll_event.acceptor,
            deathroll_event.bet,
            deathroll_event.message_id,
            deathroll_event.current_roll,
            deathroll_event.current_player,
            deathroll_event.is_finished
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding deathroll event: {e}")
            return False

    def get_event(self, message_id: int) -> Optional[DeathrollEvent]:
        """
        Get a deathroll event by its message ID.

        Args:
            message_id (int): Discord message ID

        Returns:
            Optional[DeathrollEvent]: Event if found, None otherwise
        """
        sql = """
              SELECT id, \
                     guild_id, \
                     initiator_id, \
                     acceptor_id, \
                     bet, \
                     message_id, \
                     current_roll, \
                     current_player_id, \
                     is_finished
              FROM DeathrollEvents
              WHERE message_id = %s \
              """

        try:
            result = self.execute_query(sql, (message_id,))

            if result and len(result) > 0:
                event_data = result[0]
                return DeathrollEvent(
                    event_data[0], event_data[2], event_data[3],
                    event_data[4], event_data[5], event_data[6],
                    event_data[7], bool(event_data[8])
                )
            return None

        except Exception as e:
            self.logger.error(f"Error getting deathroll event: {e}")
            return None

    def check_if_user_ingame(self, initiator_id: int, acceptor_id: int, guild_id: Optional[int] = None) -> List[
        DeathrollEvent]:
        """
        Check if either user is currently in an unfinished deathroll game.

        Args:
            initiator_id (int): Initiator's Discord user ID
            acceptor_id (int): Acceptor's Discord user ID
            guild_id (Optional[int]): Specific guild to check, or None for all guilds

        Returns:
            List[DeathrollEvent]: List of active events involving either user
        """
        if guild_id:
            sql = """
                  SELECT id, \
                         guild_id, \
                         initiator_id, \
                         acceptor_id, \
                         bet, \
                         message_id, \
                         current_roll, \
                         current_player_id, \
                         is_finished
                  FROM DeathrollEvents
                  WHERE (initiator_id = %s OR acceptor_id = %s OR initiator_id = %s OR acceptor_id = %s)
                    AND is_finished = FALSE \
                    AND guild_id = %s \
                  """
            params = (initiator_id, initiator_id, acceptor_id, acceptor_id, guild_id)
        else:
            sql = """
                  SELECT id, \
                         guild_id, \
                         initiator_id, \
                         acceptor_id, \
                         bet, \
                         message_id, \
                         current_roll, \
                         current_player_id, \
                         is_finished
                  FROM DeathrollEvents
                  WHERE (initiator_id = %s OR acceptor_id = %s OR initiator_id = %s OR acceptor_id = %s)
                    AND is_finished = FALSE \
                  """
            params = (initiator_id, initiator_id, acceptor_id, acceptor_id)

        try:
            results = self.execute_query(sql, params)

            events = []
            if results:
                for event_data in results:
                    events.append(DeathrollEvent(
                        event_data[0], event_data[2], event_data[3],
                        event_data[4], event_data[5], event_data[6],
                        event_data[7], bool(event_data[8])
                    ))

            return events

        except Exception as e:
            self.logger.error(f"Error checking if user is in game: {e}")
            return []

    def update_event(self, deathroll_event: DeathrollEvent) -> bool:
        """
        Update an existing deathroll event.

        Args:
            deathroll_event (DeathrollEvent): Event to update

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
              UPDATE DeathrollEvents
              SET current_roll      = %s, \
                  current_player_id = %s, \
                  is_finished       = %s
              WHERE message_id = %s \
              """
        values = (
            deathroll_event.current_roll,
            deathroll_event.current_player,
            deathroll_event.is_finished,
            deathroll_event.message_id
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating deathroll event: {e}")
            return False

    def delete_event(self, message_id: int) -> bool:
        """
        Delete a deathroll event by its message ID.

        Args:
            message_id (int): Discord message ID

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
              DELETE \
              FROM DeathrollEvents
              WHERE message_id = %s \
              """

        try:
            self.execute_query(sql, (message_id,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting deathroll event: {e}")
            return False

    def get_guild_active_games_count(self, guild_id: int) -> int:
        """
        Get the count of active (unfinished) deathroll games in a specific guild.

        Args:
            guild_id (int): Guild ID

        Returns:
            int: Number of active games
        """
        sql = """
              SELECT COUNT(*)
              FROM DeathrollEvents
              WHERE is_finished = FALSE \
                AND guild_id = %s \
              """

        try:
            result = self.execute_query(sql, (guild_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting active games count: {e}")
            return 0

    def get_user_guild_games(self, user_id: int, guild_id: int, include_finished: bool = False) -> List[DeathrollEvent]:
        """
        Get all deathroll games for a specific user in a specific guild.

        Args:
            user_id (int): User's Discord ID
            guild_id (int): Guild ID
            include_finished (bool, optional): Whether to include finished games. Defaults to False.

        Returns:
            List[DeathrollEvent]: List of user's games in the guild
        """
        if include_finished:
            sql = """
                  SELECT id, \
                         guild_id, \
                         initiator_id, \
                         acceptor_id, \
                         bet, \
                         message_id, \
                         current_roll, \
                         current_player_id, \
                         is_finished
                  FROM DeathrollEvents
                  WHERE (initiator_id = %s OR acceptor_id = %s) \
                    AND guild_id = %s
                  ORDER BY created_at DESC \
                  """
        else:
            sql = """
                  SELECT id, \
                         guild_id, \
                         initiator_id, \
                         acceptor_id, \
                         bet, \
                         message_id, \
                         current_roll, \
                         current_player_id, \
                         is_finished
                  FROM DeathrollEvents
                  WHERE (initiator_id = %s OR acceptor_id = %s) \
                    AND guild_id = %s \
                    AND is_finished = FALSE
                  ORDER BY created_at DESC \
                  """

        try:
            results = self.execute_query(sql, (user_id, user_id, guild_id))

            events = []
            if results:
                for event_data in results:
                    events.append(DeathrollEvent(
                        event_data[0], event_data[2], event_data[3],
                        event_data[4], event_data[5], event_data[6],
                        event_data[7], bool(event_data[8])
                    ))

            return events

        except Exception as e:
            self.logger.error(f"Error getting user guild games: {e}")
            return []

    def cleanup_old_finished_games(self, days_old: int = 7) -> int:
        """
        Clean up finished games older than specified days.

        Args:
            days_old (int): Number of days old to consider for cleanup

        Returns:
            int: Number of games cleaned up
        """
        sql = """
              DELETE \
              FROM DeathrollEvents
              WHERE is_finished = TRUE
                AND updated_at < DATE_SUB(NOW(), INTERVAL %s DAY) \
              """

        try:
            result = self.execute_query(sql, (days_old,), commit=True)
            # Get affected rows count (implementation depends on your database wrapper)
            return self.get_affected_rows() if hasattr(self, 'get_affected_rows') else 0
        except Exception as e:
            self.logger.error(f"Error cleaning up old games: {e}")
            return 0