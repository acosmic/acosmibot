from typing import Any, Dict, List, Optional, TypeVar, Generic, Type, Union, Tuple
from database import Database, get_database
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

        # Use provided database connection or get the global singleton
        if db:
            self.db = db
        else:
            self.db = get_database(self.db_host, self.db_user, self.db_password, self.db_name)

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # LAZY CONNECTION: Don't acquire connection at init time
        # This prevents connection leaks from persistent DAO instances
        # Connections will be acquired per-query and released immediately
        self.connection = None

    def __enter__(self):
        """Context manager entry - allows using DAOs with 'with' statement"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is always closed"""
        self.close()
        return False  # Don't suppress exceptions

    from mysql.connector.errors import OperationalError, InterfaceError

    def execute_query(self, query: str, params: Optional[tuple] = None, commit: bool = False, return_description: bool = False) -> Union[
        Optional[List[tuple]], bool, Tuple[Optional[List[tuple]], Optional[List]]]:
        """
        Execute a SQL query with error handling and connection recovery.

        IMPORTANT: Uses per-query connection acquisition to prevent connection leaks.
        Connection is acquired from pool, used for the query, then immediately released.

        Args:
            query (str): SQL query with placeholders
            params (Optional[tuple], optional): Query parameters. Defaults to None.
            commit (bool, optional): Whether to commit the transaction. Defaults to False.
            return_description (bool, optional): Whether to return cursor description with results. Defaults to False.

        Returns:
            Union[Optional[List[tuple]], bool]: Query results for SELECT queries, True for successful commits, None/False on error
            If return_description=True, returns tuple of (results, description)
        """
        max_retries = 2
        connection = None
        cursor = None

        for attempt in range(max_retries + 1):
            try:
                # Acquire connection from pool for this query
                connection = self.db._get_pooled_connection(retries=3, retry_delay=0.05)
                if not connection:
                    raise MySQLError("Failed to get connection from pool")

                # Create cursor
                cursor = connection.cursor()

                # Execute query
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if commit:
                    connection.commit()
                    return True  # Return True for successful commit
                else:
                    results = cursor.fetchall()
                    if return_description:
                        description = cursor.description
                        return (results, description)
                    return results

            except MySQLError as err:
                self.logger.error(f"Database error (attempt {attempt + 1}): {err}")
                self.logger.error(f"Query: {query}")
                self.logger.error(f"Params: {params}")

                # Check if it's a connection error that we can retry
                if err.errno in (2006, 2013, 2014) and attempt < max_retries:  # Connection lost errors
                    self.logger.info(f"Connection error detected, retrying... (attempt {attempt + 1})")
                    continue

                if commit:
                    try:
                        if connection:
                            connection.rollback()
                    except:
                        pass
                if return_description:
                    return (None, None) if not commit else False
                return False if commit else None

            finally:
                # Always close cursor and return connection to pool
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                if connection:
                    try:
                        connection.close()  # Returns to pool
                    except:
                        pass

        # If we get here, all retries failed
        if return_description:
            return (None, None) if not commit else False
        return False if commit else None

    def execute_many(self, query: str, params_list: List[tuple], commit: bool = False) -> bool:
        """
        Execute a SQL query with multiple parameter sets (bulk operation).

        IMPORTANT: Uses per-query connection acquisition to prevent connection leaks.
        Connection is acquired from pool, used for the query, then immediately released.

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
        connection = None
        cursor = None

        for attempt in range(max_retries + 1):
            try:
                # Acquire connection from pool for this query
                connection = self.db._get_pooled_connection(retries=3, retry_delay=0.05)
                if not connection:
                    raise MySQLError("Failed to get connection from pool")

                # Create cursor
                cursor = connection.cursor()

                # Execute many with all parameter sets
                cursor.executemany(query, params_list)

                if commit:
                    connection.commit()
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
                    continue

                if commit:
                    try:
                        if connection:
                            connection.rollback()
                    except:
                        pass
                return False

            finally:
                # Always close cursor and return connection to pool
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                if connection:
                    try:
                        connection.close()  # Returns to pool
                    except:
                        pass

        # If we get here, all retries failed
        return False

    def _reconnect(self):
        """
        Legacy method - no longer needed with per-query connection acquisition.
        Kept for backward compatibility but does nothing.
        """
        pass

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

    def execute_read(self, query: str, params: Optional[tuple] = None) -> Optional[List[tuple]]:
        """
        Execute a SELECT query (convenience method for read operations).

        Args:
            query (str): SQL SELECT query with placeholders
            params (Optional[tuple], optional): Query parameters. Defaults to None.

        Returns:
            Optional[List[tuple]]: Query results, or None on error
        """
        return self.execute_query(query, params, commit=False)

    def execute_write(self, query: str, params: Optional[tuple] = None) -> Optional[int]:
        """
        Execute an INSERT, UPDATE, or DELETE query (convenience method for write operations).
        For INSERT queries, returns the last insert ID.
        For UPDATE/DELETE queries, returns True on success.

        Args:
            query (str): SQL INSERT/UPDATE/DELETE query with placeholders
            params (Optional[tuple], optional): Query parameters. Defaults to None.

        Returns:
            Optional[int]: Last insert ID for INSERT queries, True for UPDATE/DELETE, None on error
        """
        max_retries = 2
        connection = None
        cursor = None
        is_insert = query.strip().upper().startswith('INSERT')

        for attempt in range(max_retries + 1):
            try:
                # Acquire connection from pool for this query
                connection = self.db._get_pooled_connection(retries=3, retry_delay=0.05)
                if not connection:
                    raise MySQLError("Failed to get connection from pool")

                # Create cursor
                cursor = connection.cursor()

                # Execute query
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                # Commit
                connection.commit()

                # For INSERT, get lastrowid from cursor (connection-specific)
                if is_insert:
                    last_id = cursor.lastrowid
                    return last_id if last_id else None

                return True  # Success for UPDATE/DELETE

            except MySQLError as err:
                self.logger.error(f"Database error in execute_write (attempt {attempt + 1}): {err}")
                self.logger.error(f"Query: {query}")
                self.logger.error(f"Params: {params}")

                # Check if it's a connection error that we can retry
                if err.errno in (2006, 2013, 2014) and attempt < max_retries:
                    self.logger.info(f"Connection error detected, retrying... (attempt {attempt + 1})")
                    continue

                try:
                    if connection:
                        connection.rollback()
                except:
                    pass
                return None

            finally:
                # Always close cursor and return connection to pool
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                if connection:
                    try:
                        connection.close()  # Returns to pool
                    except:
                        pass

        # If we get here, all retries failed
        return None

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
            result, description = self.execute_query(query, (id_value,), return_description=True)

            if result and len(result) > 0 and description:
                # Convert tuple to dictionary
                columns = [column[0] for column in description]
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
            results, description = self.execute_query(query, return_description=True)

            entities = []
            if results and description:
                columns = [column[0] for column in description]
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
        Close method - no longer needed with per-query connection acquisition.
        Kept for backward compatibility but does nothing since connections
        are now acquired per-query and released immediately after use.
        """
        pass