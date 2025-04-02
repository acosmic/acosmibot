from typing import Optional
from database import Database
from Dao.BaseDao import BaseDao
import logging

class VaultDao(BaseDao):
    """
    Data Access Object for Vault operations.
    Provides methods to interact with the Vault table in the database.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the VaultDao with connection parameters.
        
        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(None, "Vault", db)
        
        # Create the table if it doesn't exist
        self._create_table_if_not_exists()
    
    def _create_table_if_not_exists(self) -> None:
        """
        Create the Vault table if it doesn't exist.
        """
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS Vault (
            name VARCHAR(50) PRIMARY KEY,
            currency BIGINT NOT NULL
        )
        '''
        
        # Initialize with default values if necessary
        init_sql = '''
        INSERT IGNORE INTO Vault (name, currency) VALUES ('Vault', 0)
        '''
        
        try:
            self.create_table_if_not_exists(create_table_sql)
            self.execute_query(init_sql, commit=True)
        except Exception as e:
            self.logger.error(f"Error creating Vault table: {e}")

    def get_currency(self) -> int:
        """
        Get the current amount of currency in the vault.
        
        Returns:
            int: Current vault currency
        """
        sql = 'SELECT currency FROM Vault WHERE name = %s'
        name = 'Vault'
        
        try:
            result = self.execute_query(sql, (name,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting vault currency: {e}")
            return 0
    
    def update_currency(self, new_currency: int) -> bool:
        """
        Update the vault's currency amount.
        
        Args:
            new_currency (int): New currency amount
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = 'UPDATE Vault SET currency = %s WHERE name = %s'
        name = 'Vault'
        
        try:
            self.execute_query(sql, (new_currency, name), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error updating vault currency: {e}")
            return False
    
    def add_currency(self, amount: int) -> bool:
        """
        Add currency to the vault.
        
        Args:
            amount (int): Amount to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            current = self.get_currency()
            return self.update_currency(current + amount)
        except Exception as e:
            self.logger.error(f"Error adding currency to vault: {e}")
            return False
    
    def subtract_currency(self, amount: int) -> bool:
        """
        Subtract currency from the vault.
        
        Args:
            amount (int): Amount to subtract
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            current = self.get_currency()
            new_amount = max(0, current - amount)  # Prevent negative values
            return self.update_currency(new_amount)
        except Exception as e:
            self.logger.error(f"Error subtracting currency from vault: {e}")
            return False