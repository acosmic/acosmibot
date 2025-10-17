from typing import Any, Dict, List, Optional, TypeVar, Generic, Type, Union, Tuple
from database import Database
from Entities.BaseEntity import BaseEntity
from dotenv import load_dotenv
import os
import logging
from mysql.connector import Error as MySQLError, OperationalError, InterfaceError

# Type variable for entity classes
T = TypeVar('T', bound=BaseEntity)


class BaseDao(Generic[T]):
    """
    Base Data Access Object class that provides generic CRUD operations for entities.
    This class should be extended by specific DAO implementations.
    """

    def __init__(self, entity_class: Type[T], table_name: str, db: Optional[Database] = None):
        """
        Initialize the DAO with connection parameters.

        Args:
            entity_class (Type[T]): The entity class this DAO will operate on
            table_name (str): The database table name
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        self.entity_class = entity_class
        self.table_name = table_name
        load_dotenv()

        # Load database configuration
        self.db_host = os.getenv('db_host')
        self.db_user = os.getenv('db_user')
        self.db_password = os.getenv('db_password')
        self.db_name = os.getenv('db_name')

        # Use provided database connection or create a new one
        self.db = db or Database(self.db_host, self.db_user, self.db_password, self.db_name)

        # Set up logging
        self.logger = logging.getLogger(__name__)

    from mysql.connector.errors import OperationalError, InterfaceError

    def execute_query(self, query: str, params: Optional[tuple] = None, commit: bool = False) -> Union[
        Optional[List[tuple]], bool]:
        """
        Execute a SQL query with error handling and connection recovery.

        Args:
            query (str): SQL query with placeholders
            params (Optional[tuple], optional): Query parameters. Defaults to None.
            commit (bool, optional): Whether to commit the transaction. Defaults to False.

        Returns:
            Union[Optional[List[tuple]], bool]: Query results for SELECT queries, True for successful commits, None/False on error
        """
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                # Check if connection is still alive
                if not self.db.mydb.is_connected():
                    self.logger.info("Database connection lost, attempting to reconnect...")
                    self._reconnect()

                cursor = self.db.mycursor

                # Log the query for debugging
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if commit:
                    self.db.mydb.commit()
                    return True  # Return True for successful commit
                else:
                    return cursor.fetchall()

            except MySQLError as err:
                self.logger.error(f"Database error (attempt {attempt + 1}): {err}")
                self.logger.error(f"Query: {query}")
                self.logger.error(f"Params: {params}")

                # Check if it's a connection error that we can retry
                if err.errno in (2006, 2013, 2014) and attempt < max_retries:  # Connection lost errors
                    self.logger.info(f"Connection error detected, retrying... (attempt {attempt + 1})")
                    try:
                        self._reconnect()
                        continue
                    except Exception as reconnect_err:
                        self.logger.error(f"Failed to reconnect: {reconnect_err}")

                if commit:
                    try:
                        self.db.mydb.rollback()
                    except:
                        pass
                return False if commit else None

        # If we get here, all retries failed
        return False if commit else None

    def execute_many(self, query: str, params_list: List[tuple], commit: bool = False) -> bool:
        """
        Execute a SQL query with multiple parameter sets (bulk operation).

        Args:
            query (str): SQL query with placeholders
            params_list (List[tuple]): List of parameter tuples for bulk execution
            commit (bool, optional): Whether to commit the transaction. Defaults to False.

        Returns:
            bool: True if successful, False on error
        """
        if not params_list:
            return True

        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                # Check if connection is still alive
                if not self.db.mydb.is_connected():
                    self.logger.info("Database connection lost, attempting to reconnect...")
                    self._reconnect()

                cursor = self.db.mycursor

                # Execute many with all parameter sets
                cursor.executemany(query, params_list)

                if commit:
                    self.db.mydb.commit()
                    return True
                else:
                    return True

            except MySQLError as err:
                self.logger.error(f"Database error in executemany (attempt {attempt + 1}): {err}")
                self.logger.error(f"Query: {query}")
                self.logger.error(f"Number of parameter sets: {len(params_list)}")

                # Check if it's a connection error that we can retry
                if err.errno in (2006, 2013, 2014) and attempt < max_retries:  # Connection lost errors
                    self.logger.info(f"Connection error detected, retrying... (attempt {attempt + 1})")
                    try:
                        self._reconnect()
                        continue
                    except Exception as reconnect_err:
                        self.logger.error(f"Failed to reconnect: {reconnect_err}")

                if commit:
                    try:
                        self.db.mydb.rollback()
                    except:
                        pass
                return False

        # If we get here, all retries failed
        return False

    def _reconnect(self):
        """Reconnect to the database"""
        try:
            if hasattr(self.db, 'mydb') and self.db.mydb.is_connected():
                self.db.mydb.close()

            # Recreate the connection
            import mysql.connector
            self.db.mydb = mysql.connector.connect(
                host=self.db.db_host,
                user=self.db.db_user,
                password=self.db.db_password,
                database=self.db.db_name,
                autocommit=False,
                connect_timeout=10,
                use_unicode=True,
                charset='utf8mb4'
            )
            self.db.mycursor = self.db.mydb.cursor()
            self.logger.info("Database reconnection successful")

        except Exception as e:
            self.logger.error(f"Failed to reconnect to database: {e}")
            raise

    def get_last_insert_id(self) -> Optional[int]:
        """Get the last inserted ID"""
        try:
            result = self.execute_query("SELECT LAST_INSERT_ID()")
            return result[0][0] if result and result[0][0] else None
        except Exception as e:
            self.logger.error(f"Error getting last insert ID: {e}")
            return None

    def create_table_if_not_exists(self, create_table_sql: str) -> bool:
        """
        Create a table if it doesn't exist.

        Args:
            create_table_sql (str): SQL statement to create the table

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.execute_query(create_table_sql, commit=True)
            return result == True
        except Exception as e:
            self.logger.error(f"Failed to create table: {e}")
            return False

    def find_by_id(self, id_value: Any) -> Optional[T]:
        """
        Find an entity by its ID.

        Args:
            id_value (Any): ID value to search for

        Returns:
            Optional[T]: Entity if found, None otherwise
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE id = %s"
            result = self.execute_query(query, (id_value,))

            if result and len(result) > 0:
                # Convert tuple to dictionary
                columns = [column[0] for column in self.db.mycursor.description]
                entity_dict = dict(zip(columns, result[0]))

                # Create entity from dictionary
                return self.entity_class.from_dict(entity_dict)
            return None

        except Exception as e:
            self.logger.error(f"Error finding entity by ID: {e}")
            return None

    def find_all(self) -> List[T]:
        """
        Find all entities in the table.

        Returns:
            List[T]: List of entities
        """
        try:
            query = f"SELECT * FROM {self.table_name}"
            results = self.execute_query(query)

            entities = []
            if results:
                columns = [column[0] for column in self.db.mycursor.description]
                for row in results:
                    entity_dict = dict(zip(columns, row))
                    entities.append(self.entity_class.from_dict(entity_dict))

            return entities

        except Exception as e:
            self.logger.error(f"Error finding all entities: {e}")
            return []

    def save(self, entity: T) -> Optional[T]:
        """
        Save (insert or update) an entity to the database.

        Args:
            entity (T): Entity to save

        Returns:
            Optional[T]: Saved entity or None on error
        """
        # Implementation would depend on the specific entity structure
        # This is a placeholder for the derived classes to implement
        raise NotImplementedError("save method must be implemented by derived classes")

    def delete(self, id_value: Any) -> bool:
        """
        Delete an entity by its ID.

        Args:
            id_value (Any): ID of the entity to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = f"DELETE FROM {self.table_name} WHERE id = %s"
            result = self.execute_query(query, (id_value,), commit=True)
            return result == True

        except Exception as e:
            self.logger.error(f"Error deleting entity: {e}")
            return False

    def close(self) -> None:
        """
        Close the database connection.
        """
        try:
            self.db.close_connection()
        except Exception as e:
            self.logger.error(f"Error closing database connection: {e}")