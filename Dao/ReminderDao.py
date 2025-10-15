from typing import Optional, List
from datetime import datetime, timezone
from database import Database
from Dao.BaseDao import BaseDao
from Entities.Reminder import Reminder


class ReminderDao(BaseDao[Reminder]):
    """
    Data Access Object for Reminder entities.
    Provides methods to interact with the Reminders table in the database.
    """

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the ReminderDao with connection parameters.

        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(Reminder, "Reminders", db)

        # Create the table if it doesn't exist
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> None:
        """
        Create the Reminders table if it doesn't exist.
        """
        create_table_sql = """
                           CREATE TABLE IF NOT EXISTS Reminders \
                           ( \
                               id \
                               INT \
                               AUTO_INCREMENT \
                               PRIMARY \
                               KEY, \
                               user_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               guild_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               channel_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               message \
                               TEXT \
                               NOT \
                               NULL, \
                               remind_at \
                               DATETIME \
                               NOT \
                               NULL, \
                               created_at \
                               DATETIME \
                               NOT \
                               NULL, \
                               completed \
                               TINYINT \
                           ( \
                               1 \
                           ) DEFAULT 0,
                               message_url TEXT,
                               INDEX idx_remind_at \
                           ( \
                               remind_at \
                           ),
                               INDEX idx_user_id \
                           ( \
                               user_id \
                           ),
                               INDEX idx_completed \
                           ( \
                               completed \
                           )
                               ) \
                           """
        self.create_table_if_not_exists(create_table_sql)

    def add_reminder(self, reminder: Reminder) -> bool:
        """
        Add a new reminder to the database.

        Args:
            reminder (Reminder): Reminder to add

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
              INSERT INTO Reminders (user_id, guild_id, channel_id, message, remind_at, created_at, message_url)
              VALUES (%s, %s, %s, %s, %s, %s, %s) \
              """

        # Convert timezone-aware datetimes to naive UTC for MySQL DATETIME storage
        # mysql.connector converts tz-aware to server local time, so we strip tz to force UTC storage
        remind_at_naive = reminder.remind_at.astimezone(timezone.utc).replace(tzinfo=None) if reminder.remind_at.tzinfo else reminder.remind_at
        created_at_naive = reminder.created_at.astimezone(timezone.utc).replace(tzinfo=None) if reminder.created_at.tzinfo else reminder.created_at

        self.logger.info(f"Saving reminder: remind_at={remind_at_naive} (naive UTC), user_id={reminder.user_id}")

        values = (
            reminder.user_id,
            reminder.guild_id,
            reminder.channel_id,
            reminder.message,
            remind_at_naive,
            created_at_naive,
            reminder.message_url
        )

        try:
            self.execute_query(sql, values, commit=True)
            self.logger.info(f"✅ Reminder saved successfully with remind_at={remind_at_naive}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error adding reminder: {e}", exc_info=True)
            return False

    def get_due_reminders(self) -> List[Reminder]:
        """
        Get all reminders that are due and not completed.

        Returns:
            List[Reminder]: List of due reminders
        """
        sql = """
              SELECT id, \
                     user_id, \
                     guild_id, \
                     channel_id, \
                     message, \
                     remind_at, \
                     created_at, \
                     completed, \
                     message_url
              FROM Reminders
              WHERE remind_at <= %s \
                AND completed = 0
              ORDER BY remind_at ASC \
              """

        try:
            # Use naive UTC datetime to match how we store in the database
            now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            self.logger.info(f"Querying for reminders due before: {now_utc_naive} (naive UTC)")

            results = self.execute_query(sql, (now_utc_naive,))
            reminders = []
            if results:
                self.logger.info(f"✅ Found {len(results)} due reminder(s) in database")
                for row in results:
                    reminder = Reminder(
                        id=row[0],
                        user_id=row[1],
                        guild_id=row[2],
                        channel_id=row[3],
                        message=row[4],
                        remind_at=row[5],
                        created_at=row[6],
                        completed=bool(row[7]),
                        message_url=row[8] if row[8] else ""
                    )
                    self.logger.info(f"  - Reminder ID {reminder.id}: due at {reminder.remind_at} (from DB)")
                    reminders.append(reminder)
            else:
                self.logger.debug("No due reminders found in database")
            return reminders
        except Exception as e:
            self.logger.error(f"❌ Error getting due reminders: {e}", exc_info=True)
            return []

    def mark_completed(self, reminder_id: int) -> bool:
        """
        Mark a reminder as completed.

        Args:
            reminder_id (int): ID of the reminder to mark as completed

        Returns:
            bool: True if successful, False otherwise
        """
        sql = "UPDATE Reminders SET completed = 1 WHERE id = %s"

        try:
            result = self.execute_query(sql, (reminder_id,), commit=True)
            return result == True
        except Exception as e:
            self.logger.error(f"Error marking reminder as completed: {e}")
            return False

    def get_user_reminders(self, user_id: int, guild_id: int, include_completed: bool = False) -> List[Reminder]:
        """
        Get all reminders for a specific user in a guild.

        Args:
            user_id (int): Discord user ID
            guild_id (int): Discord guild ID
            include_completed (bool): Whether to include completed reminders

        Returns:
            List[Reminder]: List of reminders
        """
        if include_completed:
            sql = """
                  SELECT id, \
                         user_id, \
                         guild_id, \
                         channel_id, \
                         message, \
                         remind_at, \
                         created_at, \
                         completed, \
                         message_url
                  FROM Reminders
                  WHERE user_id = %s \
                    AND guild_id = %s
                  ORDER BY remind_at DESC LIMIT 10 \
                  """
        else:
            sql = """
                  SELECT id, \
                         user_id, \
                         guild_id, \
                         channel_id, \
                         message, \
                         remind_at, \
                         created_at, \
                         completed, \
                         message_url
                  FROM Reminders
                  WHERE user_id = %s \
                    AND guild_id = %s \
                    AND completed = 0
                  ORDER BY remind_at ASC \
                  """

        try:
            results = self.execute_query(sql, (user_id, guild_id))
            reminders = []
            if results:
                for row in results:
                    reminder = Reminder(
                        id=row[0],
                        user_id=row[1],
                        guild_id=row[2],
                        channel_id=row[3],
                        message=row[4],
                        remind_at=row[5],
                        created_at=row[6],
                        completed=bool(row[7]),
                        message_url=row[8] if row[8] else ""
                    )
                    reminders.append(reminder)
            return reminders
        except Exception as e:
            self.logger.error(f"Error getting user reminders: {e}")
            return []

    def delete_reminder(self, reminder_id: int, user_id: int) -> bool:
        """
        Delete a reminder (only if it belongs to the user).

        Args:
            reminder_id (int): ID of the reminder
            user_id (int): Discord user ID (for verification)

        Returns:
            bool: True if successful, False otherwise
        """
        sql = "DELETE FROM Reminders WHERE id = %s AND user_id = %s"

        try:
            result = self.execute_query(sql, (reminder_id, user_id), commit=True)
            return result == True
        except Exception as e:
            self.logger.error(f"Error deleting reminder: {e}")
            return False

    def get_reminder_by_id(self, reminder_id: int) -> Optional[Reminder]:
        """
        Get a specific reminder by its ID.

        Args:
            reminder_id (int): ID of the reminder

        Returns:
            Optional[Reminder]: Reminder if found, None otherwise
        """
        sql = """
              SELECT id, \
                     user_id, \
                     guild_id, \
                     channel_id, \
                     message, \
                     remind_at, \
                     created_at, \
                     completed, \
                     message_url
              FROM Reminders
              WHERE id = %s \
              """

        try:
            result = self.execute_query(sql, (reminder_id,))
            if result and len(result) > 0:
                row = result[0]
                return Reminder(
                    id=row[0],
                    user_id=row[1],
                    guild_id=row[2],
                    channel_id=row[3],
                    message=row[4],
                    remind_at=row[5],
                    created_at=row[6],
                    completed=bool(row[7]),
                    message_url=row[8] if row[8] else ""
                )
            return None
        except Exception as e:
            self.logger.error(f"Error getting reminder by ID: {e}")
            return None

    def get_all_active_reminders(self) -> List[Reminder]:
        """
        Get all active (not completed) reminders across all guilds.
        Useful for admin/debugging purposes.

        Returns:
            List[Reminder]: List of all active reminders
        """
        sql = """
              SELECT id, \
                     user_id, \
                     guild_id, \
                     channel_id, \
                     message, \
                     remind_at, \
                     created_at, \
                     completed, \
                     message_url
              FROM Reminders
              WHERE completed = 0
              ORDER BY remind_at ASC \
              """

        try:
            results = self.execute_query(sql)
            reminders = []
            if results:
                for row in results:
                    reminder = Reminder(
                        id=row[0],
                        user_id=row[1],
                        guild_id=row[2],
                        channel_id=row[3],
                        message=row[4],
                        remind_at=row[5],
                        created_at=row[6],
                        completed=bool(row[7]),
                        message_url=row[8] if row[8] else ""
                    )
                    reminders.append(reminder)
            return reminders
        except Exception as e:
            self.logger.error(f"Error getting all active reminders: {e}")
            return []