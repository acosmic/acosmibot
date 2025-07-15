from typing import Any, Dict, List, Optional, TypeVar, Generic, Type, Union, Tuple
from database import Database
from Entities.BaseEntity import BaseEntity
from dotenv import load_dotenv
import os
import logging
from mysql.connector import Error as MySQLError

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

    def execute_query(self, query: str, params: Optional[tuple] = None, commit: bool = False) -> Union[
        Optional[List[tuple]], bool]:
        """
        Execute a SQL query with error handling.

        Args:
            query (str): SQL query with placeholders
            params (Optional[tuple], optional): Query parameters. Defaults to None.
            commit (bool, optional): Whether to commit the transaction. Defaults to False.

        Returns:
            Union[Optional[List[tuple]], bool]: Query results for SELECT queries, True for successful commits, None/False on error
        """
        try:
            cursor = self.db.mycursor

            # Log the query for debugging
            # self.logger.debug(f"Executing query: {query}")
            if params:
                # self.logger.debug(f"With params: {params}")
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if commit:
                self.db.mydb.commit()
                return True  # Return True for successful commit
            else:
                return cursor.fetchall()

        except MySQLError as err:
            self.logger.error(f"Database error: {err}")
            self.logger.error(f"Query: {query}")
            self.logger.error(f"Params: {params}")
            if commit:
                self.db.mydb.rollback()
            return False if commit else None

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