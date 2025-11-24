import os
import mysql.connector
from mysql.connector import pooling
import logging

logger = logging.getLogger(__name__)

# Global database instance (singleton)
_global_database = None


def get_database(db_host=None, db_user=None, db_password=None, db_name=None, pool_size=None):
    """
    Get the global database singleton instance.

    Creates the instance on first call, subsequent calls return the same instance.
    All DAOs should use this function to get a Database instance instead of creating new ones.

    Args:
        db_host: Database host (used only on first initialization)
        db_user: Database user (used only on first initialization)
        db_password: Database password (used only on first initialization)
        db_name: Database name (used only on first initialization)
        pool_size: Pool size (used only on first initialization, defaults to DB_POOL_SIZE env var or 10)

    Returns:
        The global Database singleton instance
    """
    global _global_database

    if _global_database is None:
        # Use env var DB_POOL_SIZE if pool_size not provided, default to 10 for API safety
        if pool_size is None:
            pool_size = int(os.getenv('DB_POOL_SIZE', '10'))
        _global_database = Database(db_host, db_user, db_password, db_name, pool_size=pool_size)

    return _global_database


class Database:
    """
    Database connection manager with connection pooling support.
    Uses MySQL connection pooling to reuse connections across the application.
    """

    # Class-level connection pools (one per database configuration)
    _pools = {}

    def __init__(self, db_host=None, db_user=None, db_password=None, db_name=None, use_test_db=False, pool_name=None, pool_size=32):
        """
        Initialize database connection with pooling support.

        Args:
            db_host: Database host
            db_user: Database user
            db_password: Database password
            db_name: Database name
            use_test_db: Use test database credentials
            pool_name: Name for the connection pool (auto-generated if None)
            pool_size: Number of connections in the pool (default: 32, max 32)
        """
        if use_test_db:
            self.db_host = db_host or os.getenv('test_db_host')
            self.db_user = db_user or os.getenv('test_db_user')
            self.db_password = db_password or os.getenv('test_db_password')
            self.db_name = db_name or os.getenv('test_db_name')
            pool_name = pool_name or "test_pool"
        else:
            self.db_host = db_host or os.getenv('db_host')
            self.db_user = db_user or os.getenv('db_user')
            self.db_password = db_password or os.getenv('db_password')
            self.db_name = db_name or os.getenv('db_name')
            pool_name = pool_name or "default_pool"

        self.pool_name = pool_name
        self.use_test_db = use_test_db

        # Create or get the connection pool with proper credentials
        self._ensure_pool_exists(
            pool_name=pool_name,
            host=self.db_host,
            user=self.db_user,
            password=self.db_password,
            database=self.db_name,
            pool_size=pool_size
        )

        # Don't auto-acquire connection - let each DAO get its own
        # This prevents race conditions from shared global connection
        self.mydb = None
        self.mycursor = None

    @classmethod
    def _ensure_pool_exists(cls, pool_name, host, user, password, database, pool_size=5):
        """
        Create a connection pool if it doesn't already exist.

        Args:
            pool_name: Name for the connection pool
            host: Database host
            user: Database user
            password: Database password
            database: Database name
            pool_size: Number of connections in the pool
        """
        if pool_name not in cls._pools:
            try:
                pool = pooling.MySQLConnectionPool(
                    pool_name=pool_name,
                    pool_size=pool_size,
                    pool_reset_session=False,
                    host=host,
                    user=user,
                    password=password,
                    database=database,
                    autocommit=True,
                    connection_timeout=30,
                    raise_on_warnings=False,
                    use_unicode=True,
                    charset='utf8mb4',
                    collation='utf8mb4_unicode_ci'
                )
                cls._pools[pool_name] = pool
                logger.info(f"Created connection pool '{pool_name}' with {pool_size} connections")
            except Exception as e:
                logger.error(f"Failed to create connection pool '{pool_name}': {e}")
                raise

    def _get_pooled_connection(self, retries=3, retry_delay=0.05):
        """
        Get a connection from the pool with retry logic.

        Args:
            retries: Number of times to retry if pool is exhausted (default: 3)
            retry_delay: Delay in seconds between retries (default: 0.05)

        Returns:
            A MySQL connection from the pool, or None if failed
        """
        import time

        for attempt in range(retries):
            try:
                pool = self._pools.get(self.pool_name)
                if not pool:
                    logger.error(f"Connection pool '{self.pool_name}' not found")
                    if attempt < retries - 1:
                        time.sleep(retry_delay)
                    continue

                connection = pool.get_connection()
                if connection:
                    # Connection obtained from pool, return it even if not immediately connected
                    # The pool handles reconnection internally
                    return connection
                else:
                    if attempt < retries - 1:
                        time.sleep(retry_delay)
                    continue

            except Exception as e:
                # Only log as error on last attempt to reduce spam
                if attempt == retries - 1:
                    logger.error(f"Failed to get connection from pool after {retries} attempts: {e}")
                elif attempt < retries - 1:
                    time.sleep(retry_delay)

        return None

    def close_connection(self):
        """Close the current connection and return it to the pool."""
        if self.mycursor:
            try:
                self.mycursor.close()
            except Exception as e:
                logger.warning(f"Error closing cursor: {e}")

        if self.mydb:
            try:
                # Safely check if connection is alive before closing
                # (is_connected() can fail if connection is in bad state)
                try:
                    is_alive = self.mydb.is_connected()
                except Exception:
                    # Connection is in bad state, but we still want to try closing it
                    is_alive = True

                if is_alive:
                    self.mydb.close()  # Returns connection to pool, doesn't actually close it
                    logger.debug("Connection returned to pool")
            except Exception as e:
                logger.debug(f"Note while closing connection: {e}")

    @classmethod
    def get_pool_stats(cls, pool_name="default_pool"):
        """
        Get connection pool statistics for monitoring.

        Args:
            pool_name: Name of the pool to check

        Returns:
            dict: Pool statistics including pool size and current connections
        """
        try:
            pool = cls._pools.get(pool_name)
            if not pool:
                return {"error": f"Pool '{pool_name}' not found"}

            # Try to get pool size from the pool object
            pool_size = pool.pool_size if hasattr(pool, 'pool_size') else "unknown"

            return {
                "pool_name": pool_name,
                "pool_size": pool_size,
                "status": "active"
            }
        except Exception as e:
            return {"error": str(e)}

    @classmethod
    def close_all_pools(cls):
        """Close all connection pools (useful for graceful shutdown)."""
        for pool_name, pool in cls._pools.items():
            try:
                # Close all connections in the pool
                while True:
                    try:
                        conn = pool.get_connection()
                        if conn.is_connected():
                            conn.close()
                    except:
                        break
                logger.info(f"Closed connection pool '{pool_name}'")
            except Exception as e:
                logger.warning(f"Error closing pool '{pool_name}': {e}")
        cls._pools.clear()

