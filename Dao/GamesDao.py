from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from database import Database
from Dao.BaseDao import BaseDao
from Entities.Game import Game, CoinflipGame
import json


class GamesDao(BaseDao[Game]):
    """
    Main Games DAO - handles universal game statistics and leaderboards
    """

    def __init__(self, db: Optional[Database] = None):
        super().__init__(Game, "Games", db)

    def add_game(self, user_id: int, guild_id: int, game_type: str,
                 amount_bet: int, amount_won: int, amount_lost: int,
                 result: str) -> Optional[int]:
        """
        Add a game record and return the game_id for specific game tables

        Returns:
            Optional[int]: game_id if successful, None otherwise
        """
        sql = """
            INSERT INTO Games (user_id, guild_id, game_type, amount_bet, 
                             amount_won, amount_lost, result, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (user_id, guild_id, game_type, amount_bet,
                  amount_won, amount_lost, result, datetime.now())

        try:
            result = self.execute_query(sql, values, commit=True)
            # Return the last inserted ID
            return self.get_last_insert_id()
        except Exception as e:
            self.logger.error(f"Error adding game: {e}")
            return None

    def get_user_game_stats(self, user_id: int, guild_id: Optional[int] = None,
                            game_type: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive game statistics for a user"""
        where_clauses = ["user_id = %s"]
        params = [user_id]

        if guild_id:
            where_clauses.append("guild_id = %s")
            params.append(guild_id)

        if game_type:
            where_clauses.append("game_type = %s")
            params.append(game_type)

        where_clause = " AND ".join(where_clauses)

        sql = f"""
            SELECT 
                game_type,
                COUNT(*) as total_games,
                SUM(amount_bet) as total_bet,
                SUM(amount_won) as total_won,
                SUM(amount_lost) as total_lost,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'lose' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END) as draws
            FROM Games 
            WHERE {where_clause}
            GROUP BY game_type
        """

        try:
            results = self.execute_query(sql, params)

            stats = {}
            total_stats = {
                'total_games': 0, 'total_bet': 0, 'total_won': 0, 'total_lost': 0,
                'wins': 0, 'losses': 0, 'draws': 0, 'net_profit': 0
            }

            for row in results:
                game_type = row[0]
                game_stats = {
                    'total_games': row[1],
                    'total_bet': row[2],
                    'total_won': row[3],
                    'total_lost': row[4],
                    'wins': row[5],
                    'losses': row[6],
                    'draws': row[7],
                    'win_rate': (row[5] / row[1] * 100) if row[1] > 0 else 0,
                    'net_profit': row[3] - row[4]
                }
                stats[game_type] = game_stats

                # Add to totals
                for key in total_stats:
                    if key == 'net_profit':
                        continue
                    total_stats[key] += game_stats[key]

            total_stats['net_profit'] = total_stats['total_won'] - total_stats['total_lost']
            total_stats['win_rate'] = (total_stats['wins'] / total_stats['total_games'] * 100) if total_stats[
                                                                                                      'total_games'] > 0 else 0

            stats['total'] = total_stats
            return stats

        except Exception as e:
            self.logger.error(f"Error getting user game stats: {e}")
            return {}

    def get_leaderboard(self, guild_id: Optional[int] = None,
                        game_type: Optional[str] = None,
                        stat_type: str = 'net_profit',
                        limit: int = 10) -> List[Tuple]:
        """
        Get leaderboard for various statistics

        Args:
            guild_id: Specific guild (None for global)
            game_type: Specific game type (None for all games)
            stat_type: 'net_profit', 'total_won', 'total_games', 'win_rate'
            limit: Number of results
        """
        where_clauses = []
        params = []

        if guild_id:
            where_clauses.append("guild_id = %s")
            params.append(guild_id)

        if game_type:
            where_clauses.append("game_type = %s")
            params.append(game_type)

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        if stat_type == 'net_profit':
            order_by = "ORDER BY (SUM(amount_won) - SUM(amount_lost)) DESC"
        elif stat_type == 'total_won':
            order_by = "ORDER BY SUM(amount_won) DESC"
        elif stat_type == 'total_games':
            order_by = "ORDER BY COUNT(*) DESC"
        elif stat_type == 'win_rate':
            order_by = "ORDER BY (SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) / COUNT(*)) DESC"
        else:
            order_by = "ORDER BY (SUM(amount_won) - SUM(amount_lost)) DESC"

        sql = f"""
            SELECT 
                user_id,
                COUNT(*) as total_games,
                SUM(amount_won) as total_won,
                SUM(amount_lost) as total_lost,
                (SUM(amount_won) - SUM(amount_lost)) as net_profit,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                (SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) / COUNT(*) * 100) as win_rate
            FROM Games 
            {where_clause}
            GROUP BY user_id
            HAVING total_games >= 3
            {order_by}
            LIMIT %s
        """

        params.append(limit)

        try:
            return self.execute_query(sql, params) or []
        except Exception as e:
            self.logger.error(f"Error getting leaderboard: {e}")
            return []


class CoinflipDao(BaseDao[CoinflipGame]):
    """
    Specific DAO for Coinflip games
    """

    def __init__(self, db: Optional[Database] = None):
        super().__init__(CoinflipGame, "Coinflip_Games", db)

    def add_coinflip_game(self, game_id: int, user_id: int, guild_id: int,
                          user_call: str, actual_result: str, amount_bet: int,
                          amount_won: int, amount_lost: int) -> bool:
        """Add a specific coinflip game record"""
        sql = """
            INSERT INTO Coinflip_Games (game_id, user_id, guild_id, user_call, 
                                      actual_result, amount_bet, amount_won, 
                                      amount_lost, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (game_id, user_id, guild_id, user_call, actual_result,
                  amount_bet, amount_won, amount_lost, datetime.now())

        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding coinflip game: {e}")
            return False

    def get_coinflip_history(self, user_id: int, guild_id: Optional[int] = None,
                             limit: int = 10) -> List[CoinflipGame]:
        """Get coinflip history for a user"""
        where_clause = "WHERE user_id = %s"
        params = [user_id]

        if guild_id:
            where_clause += " AND guild_id = %s"
            params.append(guild_id)

        sql = f"""
            SELECT * FROM Coinflip_Games 
            {where_clause}
            ORDER BY created_at DESC 
            LIMIT %s
        """
        params.append(limit)

        try:
            results = self.execute_query(sql, params)
            return [self._row_to_entity(row) for row in results] if results else []
        except Exception as e:
            self.logger.error(f"Error getting coinflip history: {e}")
            return []

    def get_coinflip_stats(self, user_id: int, guild_id: Optional[int] = None) -> Dict[str, Any]:
        """Get detailed coinflip statistics"""
        where_clause = "WHERE user_id = %s"
        params = [user_id]

        if guild_id:
            where_clause += " AND guild_id = %s"
            params.append(guild_id)

        sql = f"""
            SELECT 
                COUNT(*) as total_games,
                SUM(amount_bet) as total_bet,
                SUM(amount_won) as total_won,
                SUM(amount_lost) as total_lost,
                SUM(CASE WHEN user_call = actual_result THEN 1 ELSE 0 END) as correct_calls,
                SUM(CASE WHEN user_call = 'Heads' THEN 1 ELSE 0 END) as heads_calls,
                SUM(CASE WHEN user_call = 'Tails' THEN 1 ELSE 0 END) as tails_calls,
                SUM(CASE WHEN actual_result = 'Heads' THEN 1 ELSE 0 END) as heads_results,
                SUM(CASE WHEN actual_result = 'Tails' THEN 1 ELSE 0 END) as tails_results
            FROM Coinflip_Games 
            {where_clause}
        """

        try:
            result = self.execute_query(sql, params)
            if result and result[0][0] > 0:  # If there are games
                row = result[0]
                return {
                    'total_games': row[0],
                    'total_bet': row[1],
                    'total_won': row[2],
                    'total_lost': row[3],
                    'net_profit': row[2] - row[3],
                    'correct_calls': row[4],
                    'accuracy': (row[4] / row[0] * 100) if row[0] > 0 else 0,
                    'heads_preference': (row[5] / row[0] * 100) if row[0] > 0 else 0,
                    'tails_preference': (row[6] / row[0] * 100) if row[0] > 0 else 0,
                    'heads_frequency': (row[7] / row[0] * 100) if row[0] > 0 else 0,
                    'tails_frequency': (row[8] / row[0] * 100) if row[0] > 0 else 0
                }
            return {}
        except Exception as e:
            self.logger.error(f"Error getting coinflip stats: {e}")
            return {}


# Similar pattern for other games...
class DeathrollDao(BaseDao):
    """DAO for Deathroll games"""
    pass


class RPSDao(BaseDao):
    """DAO for Rock Paper Scissors games"""
    pass


class SlotsDao(BaseDao):
    """DAO for Slots games"""
    pass