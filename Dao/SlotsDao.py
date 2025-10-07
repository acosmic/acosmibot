from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from database import Database
from Dao.BaseDao import BaseDao
from Entities.SlotEvent import SlotEvent
import logging


class SlotsDao(BaseDao[SlotEvent]):
    """
    Data Access Object for SlotEvent entities.
    Integrates with the unified Games system.
    """

    def __init__(self, db: Optional[Database] = None):
        super().__init__(SlotEvent, "Slots_Games", db)
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> None:
        """
        Create the Slots_Games table if it doesn't exist.
        This table stores slot-specific details and references the Games table.
        """
        create_table_sql = '''
                           CREATE TABLE IF NOT EXISTS Slots_Games \
                           ( \
                               id \
                               BIGINT \
                               AUTO_INCREMENT \
                               PRIMARY \
                               KEY, \
                               game_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               user_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               guild_id \
                               BIGINT \
                               NOT \
                               NULL, \
                               symbols \
                               JSON \
                               NOT \
                               NULL, \
                               multiplier \
                               DECIMAL \
                           ( \
                               4, \
                               2 \
                           ) DEFAULT 0.00,
                               amount_bet INT NOT NULL,
                               amount_won INT NOT NULL DEFAULT 0,
                               amount_lost INT NOT NULL DEFAULT 0,
                               created_at DATETIME NOT NULL,
                               INDEX idx_user_guild \
                           ( \
                               user_id, \
                               guild_id \
                           ),
                               INDEX idx_game_id \
                           ( \
                               game_id \
                           )
                               ) \
                           '''
        self.create_table_if_not_exists(create_table_sql)

    def add_slots_game(self, game_id: int, user_id: int, guild_id: int,
                       slot1: str, slot2: str, slot3: str,
                       amount_bet: int, amount_won: int, amount_lost: int) -> bool:
        """
        Add a specific slots game record linked to a Games table entry.

        Args:
            game_id: Reference to Games table entry
            user_id: Discord user ID
            guild_id: Discord guild ID
            slot1, slot2, slot3: Slot symbols
            amount_bet: Bet amount
            amount_won: Amount won (0 if lost)
            amount_lost: Amount lost (0 if won)

        Returns:
            bool: True if successful, False otherwise
        """
        import json

        # Create symbols JSON array
        symbols = json.dumps([slot1, slot2, slot3])

        # Calculate multiplier
        multiplier = 0.0
        if amount_won > 0:
            multiplier = amount_won / amount_bet if amount_bet > 0 else 0.0

        sql = """
              INSERT INTO Slots_Games (game_id, user_id, guild_id, symbols, multiplier,
                                       amount_bet, amount_won, amount_lost, created_at)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) \
              """
        values = (
            game_id,
            user_id,
            guild_id,
            symbols,
            multiplier,
            amount_bet,
            amount_won,
            amount_lost,
            datetime.now()
        )

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding slots game: {e}")
            return False

    def get_slots_history(self, user_id: int, guild_id: Optional[int] = None,
                          limit: int = 10) -> List[Dict]:
        """
        Get slots history for a user.

        Args:
            user_id: Discord user ID
            guild_id: Optional guild filter
            limit: Number of results

        Returns:
            List of slot game records
        """
        import json

        where_clause = "WHERE user_id = %s"
        params = [user_id]

        if guild_id:
            where_clause += " AND guild_id = %s"
            params.append(guild_id)

        sql = f"""
            SELECT * FROM Slots_Games 
            {where_clause}
            ORDER BY created_at DESC 
            LIMIT %s
        """
        params.append(limit)

        try:
            results = self.execute_query(sql, params)
            if results:
                history = []
                for row in results:
                    record = self._row_to_dict(row)
                    # Parse symbols JSON if it exists
                    if 'symbols' in record and record['symbols']:
                        try:
                            record['symbols'] = json.loads(record['symbols'])
                        except:
                            pass
                    history.append(record)
                return history
            return []
        except Exception as e:
            self.logger.error(f"Error getting slots history: {e}")
            return []

    def get_slots_stats(self, user_id: int, guild_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get detailed slots statistics for a user.

        Args:
            user_id: Discord user ID
            guild_id: Optional guild filter

        Returns:
            Dictionary of statistics
        """
        where_clause = "WHERE user_id = %s"
        params = [user_id]

        if guild_id:
            where_clause += " AND guild_id = %s"
            params.append(guild_id)

        sql = f"""
            SELECT 
                COUNT(*) as total_spins,
                SUM(amount_bet) as total_bet,
                SUM(amount_won) as total_won,
                SUM(amount_lost) as total_lost,
                SUM(CASE WHEN amount_won > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN amount_lost > 0 THEN 1 ELSE 0 END) as losses,
                MAX(amount_won) as biggest_win
            FROM Slots_Games 
            {where_clause}
        """

        try:
            result = self.execute_query(sql, params)
            if result and result[0][0] > 0:
                row = result[0]
                return {
                    'total_spins': row[0],
                    'total_bet': row[1],
                    'total_won': row[2],
                    'total_lost': row[3],
                    'net_profit': row[2] - row[3],
                    'wins': row[4],
                    'losses': row[5],
                    'win_rate': (row[4] / row[0] * 100) if row[0] > 0 else 0,
                    'biggest_win': row[6]
                }
            return {}
        except Exception as e:
            self.logger.error(f"Error getting slots stats: {e}")
            return {}

    def _row_to_dict(self, row) -> Dict:
        """Convert database row to dictionary"""
        import json

        symbols_data = row[4]
        # Parse JSON if it's a string
        if isinstance(symbols_data, str):
            try:
                symbols_data = json.loads(symbols_data)
            except:
                symbols_data = row[4]

        return {
            'id': row[0],
            'game_id': row[1],
            'user_id': row[2],
            'guild_id': row[3],
            'symbols': symbols_data,
            'multiplier': float(row[5]) if row[5] else 0.0,
            'amount_bet': row[6],
            'amount_won': row[7],
            'amount_lost': row[8],
            'created_at': row[9]
        }

    # Legacy support methods (kept for backward compatibility)
    def get_slot_wins(self, discord_id: int) -> int:
        """Get number of slot wins (legacy method)"""
        stats = self.get_slots_stats(discord_id)
        return stats.get('wins', 0)

    def get_slot_losses(self, discord_id: int) -> int:
        """Get number of slot losses (legacy method)"""
        stats = self.get_slots_stats(discord_id)
        return stats.get('losses', 0)

    def get_total_slots(self, discord_id: int) -> int:
        """Get total spins (legacy method)"""
        stats = self.get_slots_stats(discord_id)
        return stats.get('total_spins', 0)

    def get_total_won(self, discord_id: int) -> int:
        """Get total won (legacy method)"""
        stats = self.get_slots_stats(discord_id)
        return stats.get('total_won', 0)

    def get_total_lost(self, discord_id: int) -> int:
        """Get total lost (legacy method)"""
        stats = self.get_slots_stats(discord_id)
        return stats.get('total_lost', 0)