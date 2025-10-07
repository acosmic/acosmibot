from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from database import Database
from Dao.BaseDao import BaseDao
from Entities.CoinflipEvent import CoinflipEvent
import logging

class CoinflipDao(BaseDao[CoinflipEvent]):
    """
    Data Access Object for CoinflipEvent entities.
    Provides methods to interact with the Coinflip table in the database.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the CoinflipDao with connection parameters.
        
        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(CoinflipEvent, "Coinflip", db)
        
        # Create the table if it doesn't exist
        self._create_table_if_not_exists()
    
    def _create_table_if_not_exists(self) -> None:
        """
        Create the Coinflip table if it doesn't exist.
        """
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS Coinflip (
            id INT AUTO_INCREMENT PRIMARY KEY,
            discord_id BIGINT NOT NULL,
            guess VARCHAR(10) NOT NULL,
            result VARCHAR(10) NOT NULL,
            amount_won INT NOT NULL,
            amount_lost INT NOT NULL,
            timestamp DATETIME NOT NULL
        )
        '''
        self.create_table_if_not_exists(create_table_sql)
    
    def add_new_event(self, coinflip_event: CoinflipEvent) -> bool:
        """
        Add a new coinflip event to the database.
        
        Args:
            coinflip_event (CoinflipEvent): Coinflip event to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            INSERT INTO Coinflip (discord_id, guess, result, amount_won, amount_lost, timestamp) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            coinflip_event.discord_id,
            coinflip_event.guess,
            coinflip_event.result,
            coinflip_event.amount_won,
            coinflip_event.amount_lost,
            coinflip_event.timestamp
        )
        
        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding coinflip event: {e}")
            return False

    def get_flip_wins(self, discord_id: int) -> int:
        """
        Get the number of coinflip wins for a user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            int: Number of wins
        """
        sql = """
            SELECT COUNT(*)
            FROM Coinflip
            WHERE discord_id = %s AND amount_won > 0
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting coinflip wins: {e}")
            return 0
    
    def get_flip_losses(self, discord_id: int) -> int:
        """
        Get the number of coinflip losses for a user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            int: Number of losses
        """
        sql = """
            SELECT COUNT(*)
            FROM Coinflip
            WHERE discord_id = %s AND amount_lost > 0
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting coinflip losses: {e}")
            return 0
    
    def get_total_flips(self, discord_id: int) -> int:
        """
        Get the total number of coinflip games played by a user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            int: Total number of games
        """
        sql = """
            SELECT COUNT(*)
            FROM Coinflip
            WHERE discord_id = %s
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total flips: {e}")
            return 0
    
    def get_total_won(self, discord_id: int) -> int:
        """
        Get the total amount won by a user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            int: Total amount won
        """
        sql = """
            SELECT SUM(amount_won)
            FROM Coinflip
            WHERE discord_id = %s
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total won: {e}")
            return 0
    
    def get_total_lost(self, discord_id: int) -> int:
        """
        Get the total amount lost by a user.
        
        Args:
            discord_id (int): Discord user ID
            
        Returns:
            int: Total amount lost
        """
        sql = """
            SELECT SUM(amount_lost)
            FROM Coinflip
            WHERE discord_id = %s
        """
        
        try:
            result = self.execute_query(sql, (discord_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error getting total lost: {e}")
            return 0

    def get_top_wins(self) -> List[Tuple]:
        """
        Get the top coinflip wins.
        
        Returns:
            List[Tuple]: List of top wins (username, amount, timestamp)
        """
        sql = """
            SELECT u.discord_username,
                c.amount_won AS largest_single_win,
                c.timestamp AS win_timestamp
            FROM Coinflip c
            JOIN Users u ON c.discord_id = u.id
            WHERE (u.id, c.amount_won) IN (
                SELECT u.id,
                    MAX(c1.amount_won) AS max_win
                FROM Coinflip c1
                JOIN Users u ON c1.discord_id = u.id
                GROUP BY u.id
            )
            ORDER BY largest_single_win DESC
            LIMIT 5;
            """
        
        try:
            return self.execute_query(sql) or []
        except Exception as e:
            self.logger.error(f"Error getting top wins: {e}")
            return []
    
    def get_top_losses(self) -> List[Tuple]:
        """
        Get the top coinflip losses.
        
        Returns:
            List[Tuple]: List of top losses (username, amount, timestamp)
        """
        sql = """
            SELECT u.discord_username,
                c.amount_lost AS largest_single_loss,
                c.timestamp AS loss_timestamp
            FROM Coinflip c
            JOIN Users u ON c.discord_id = u.id
            WHERE (u.id, c.amount_lost) IN (
                SELECT u.id,
                    MAX(c1.amount_lost) AS max_loss
                FROM Coinflip c1
                JOIN Users u ON c1.discord_id = u.id
                GROUP BY u.id
            )
            ORDER BY largest_single_loss DESC
            LIMIT 5;
            """
        
        try:
            return self.execute_query(sql) or []
        except Exception as e:
            self.logger.error(f"Error getting top losses: {e}")
            return []

    def get_coinflip_stats(self, discord_id: int, guild_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get detailed coinflip statistics for a user from the new Coinflip_Games table.

        Args:
            discord_id: Discord user ID
            guild_id: Optional guild filter

        Returns:
            Dictionary of statistics
        """
        where_clause = "WHERE user_id = %s"
        params = [discord_id]

        if guild_id:
            where_clause += " AND guild_id = %s"
            params.append(guild_id)

        # Query the NEW Coinflip_Games table
        sql = f"""
            SELECT 
                COUNT(*) as total_games,
                SUM(amount_bet) as total_bet,
                SUM(amount_won) as total_won,
                SUM(amount_lost) as total_lost,
                SUM(CASE WHEN user_call = actual_result THEN 1 ELSE 0 END) as correct_calls
            FROM Coinflip_Games 
            {where_clause}
        """

        try:
            result = self.execute_query(sql, params)
            if result and result[0][0] > 0:
                row = result[0]
                total_games = row[0]
                total_bet = row[1] if row[1] else 0
                total_won = row[2] if row[2] else 0
                total_lost = row[3] if row[3] else 0
                correct_calls = row[4] if row[4] else 0

                return {
                    'total_games': total_games,
                    'total_bet': total_bet,
                    'total_won': total_won,
                    'total_lost': total_lost,
                    'correct_calls': correct_calls,
                    'accuracy': (correct_calls / total_games * 100) if total_games > 0 else 0,
                    'net_profit': total_won - total_lost
                }
            return {}
        except Exception as e:
            self.logger.error(f"Error getting coinflip stats from Coinflip_Games: {e}")
            # Fallback to old table if new table query fails
            return self._get_coinflip_stats_legacy(discord_id)

    def _get_coinflip_stats_legacy(self, discord_id: int) -> Dict[str, Any]:
        """
        Legacy method to get stats from old Coinflip table.
        """
        sql = """
              SELECT COUNT(*)                                         as total_games, \
                     SUM(amount_won)                                  as total_won, \
                     SUM(amount_lost)                                 as total_lost, \
                     SUM(CASE WHEN amount_won > 0 THEN 1 ELSE 0 END)  as wins, \
                     SUM(CASE WHEN amount_lost > 0 THEN 1 ELSE 0 END) as losses
              FROM Coinflip
              WHERE discord_id = %s \
              """

        try:
            result = self.execute_query(sql, (discord_id,))
            if result and result[0][0] > 0:
                row = result[0]
                total_games = row[0]
                total_won = row[1] if row[1] else 0
                total_lost = row[2] if row[2] else 0
                wins = row[3] if row[3] else 0

                return {
                    'total_games': total_games,
                    'total_won': total_won,
                    'total_lost': total_lost,
                    'correct_calls': wins,
                    'accuracy': (wins / total_games * 100) if total_games > 0 else 0,
                    'net_profit': total_won - total_lost
                }
            return {}
        except Exception as e:
            self.logger.error(f"Error getting legacy coinflip stats: {e}")
            return {}
    
    def save(self, coinflip_event: CoinflipEvent) -> Optional[CoinflipEvent]:
        """
        Save a coinflip event to the database (insert only, as we don't update coinflip events).
        
        Args:
            coinflip_event (CoinflipEvent): Coinflip event to save
            
        Returns:
            Optional[CoinflipEvent]: Saved coinflip event or None on error
        """
        try:
            if self.add_new_event(coinflip_event):
                return coinflip_event
            return None
        except Exception as e:
            self.logger.error(f"Error saving coinflip event: {e}")
            return None