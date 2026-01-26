from typing import Optional, List, Dict, Any
from datetime import datetime
from database import Database
from Dao.BaseDao import BaseDao
import json


class GamesDao(BaseDao):
    """
    Unified Games DAO - single table for all game types with JSON for specifics
    """

    def __init__(self, db: Optional[Database] = None):
        super().__init__(None, "Games", db)
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> None:
        """Create the unified Games table"""
        create_table_sql = '''
                           CREATE TABLE IF NOT EXISTS Games \
                           ( \
                               id \
                               BIGINT \
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
                               game_type \
                               VARCHAR \
                           ( \
                               50 \
                           ) NOT NULL,
                               amount_bet INT NOT NULL,
                               amount_won INT NOT NULL DEFAULT 0,
                               amount_lost INT NOT NULL DEFAULT 0,
                               result VARCHAR \
                           ( \
                               20 \
                           ) NOT NULL,
                               game_data JSON,
                               created_at DATETIME NOT NULL,
                               INDEX idx_user_guild \
                           ( \
                               user_id, \
                               guild_id \
                           ),
                               INDEX idx_game_type \
                           ( \
                               game_type \
                           ),
                               INDEX idx_created_at \
                           ( \
                               created_at \
                           ),
                               INDEX idx_result \
                           ( \
                               result \
                           )
                               ) \
                           '''
        self.create_table_if_not_exists(create_table_sql)

    def add_game(self, user_id: int, guild_id: int, game_type: str,
                 amount_bet: int, amount_won: int, amount_lost: int,
                 result: str, game_data: Dict[str, Any] = None) -> Optional[int]:
        """
        Add a game record with optional game-specific data

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            game_type: Type of game ('coinflip', 'slots', 'deathroll', etc.)
            amount_bet: Amount wagered
            amount_won: Amount won (0 if lost)
            amount_lost: Amount lost (0 if won)
            result: 'win', 'lose', or 'draw'
            game_data: Optional dict with game-specific data

        Returns:
            int: game_id if successful, None otherwise
        """
        sql = """
              INSERT INTO Games (user_id, guild_id, game_type, amount_bet,
                                 amount_won, amount_lost, result, game_data, created_at)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) \
              """

        # Convert game_data dict to JSON string
        game_data_json = json.dumps(game_data) if game_data else None

        values = (user_id, guild_id, game_type, amount_bet,
                  amount_won, amount_lost, result, game_data_json, datetime.now())

        try:
            self.execute_query(sql, values, commit=True)
            game_id = self.get_last_insert_id()
            self.logger.info(f"Added {game_type} game (id: {game_id}) for user {user_id}")
            return game_id
        except Exception as e:
            self.logger.error(f"Error adding game: {e}")
            return None

    def batch_add_games(self, games: List[Dict[str, Any]]) -> int:
        """
        Batch insert multiple games in a single transaction.

        Args:
            games: List of dicts with keys:
                - user_id: int
                - guild_id: int
                - game_type: str
                - amount_bet: int
                - amount_won: int
                - amount_lost: int
                - result: str
                - game_data: str (JSON string) or None
                - timestamp: str (datetime string) or None

        Returns:
            Number of games inserted
        """
        if not games:
            return 0

        sql = """
            INSERT INTO Games (user_id, guild_id, game_type, amount_bet,
                               amount_won, amount_lost, result, game_data, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Prepare parameter tuples for each game
        params_list = []
        for game in games:
            # Use provided timestamp or current time
            created_at = game.get("timestamp")
            if isinstance(created_at, str):
                # Convert ISO format string to datetime if needed
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = datetime.now()
            elif not created_at:
                created_at = datetime.now()

            params = (
                game["user_id"],
                game["guild_id"],
                game["game_type"],
                game["amount_bet"],
                game["amount_won"],
                game["amount_lost"],
                game["result"],
                game.get("game_data"),  # Already a JSON string or None
                created_at
            )
            params_list.append(params)

        try:
            success = self.execute_many(sql, params_list, commit=True)
            if success:
                self.logger.info(f"Batch inserted {len(games)} game records")
                return len(games)
            else:
                self.logger.error("Batch insert failed")
                return 0
        except Exception as e:
            self.logger.error(f"Error batch inserting games: {e}")
            return 0

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
                SUM(CASE WHEN result = 'draw' OR result = 'push' THEN 1 ELSE 0 END) as draws
            FROM Games
            WHERE {where_clause}
            GROUP BY game_type
        """
        # Note: This query uses aggregate functions and GROUP BY, not SELECT *, so no changes needed

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
                    'total_bet': row[2] or 0,
                    'total_won': row[3] or 0,
                    'total_lost': row[4] or 0,
                    'wins': row[5],
                    'losses': row[6],
                    'draws': row[7],
                    'win_rate': (row[5] / row[1] * 100) if row[1] > 0 else 0,
                    'net_profit': (row[3] or 0) - (row[4] or 0)
                }
                stats[game_type] = game_stats

                # Add to totals
                for key in ['total_games', 'total_bet', 'total_won', 'total_lost', 'wins', 'losses', 'draws']:
                    total_stats[key] += game_stats[key]

            total_stats['net_profit'] = total_stats['total_won'] - total_stats['total_lost']
            total_stats['win_rate'] = (total_stats['wins'] / total_stats['total_games'] * 100) if total_stats[
                                                                                                      'total_games'] > 0 else 0

            stats['total'] = total_stats
            return stats

        except Exception as e:
            self.logger.error(f"Error getting user game stats: {e}")
            return {}

    def get_game_history(self, user_id: int, guild_id: Optional[int] = None,
                         game_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Get game history with full details including game_data
        """
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
            SELECT id, user_id, guild_id, game_type, amount_bet, amount_won,
                   amount_lost, result, game_data, created_at
            FROM Games
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
        """
        params.append(limit)

        try:
            results = self.execute_query(sql, params)
            if results:
                history = []
                for row in results:
                    game = {
                        'id': row[0],
                        'user_id': row[1],
                        'guild_id': row[2],
                        'game_type': row[3],
                        'amount_bet': row[4],
                        'amount_won': row[5],
                        'amount_lost': row[6],
                        'result': row[7],
                        'game_data': json.loads(row[8]) if row[8] else {},
                        'created_at': row[9]
                    }
                    history.append(game)
                return history
            return []
        except Exception as e:
            self.logger.error(f"Error getting game history: {e}")
            return []

    def get_specific_game_stats(self, user_id: int, game_type: str,
                                guild_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get stats for a specific game type
        Useful for game-specific stats like coinflip accuracy
        """
        where_clauses = ["user_id = %s", "game_type = %s"]
        params = [user_id, game_type]

        if guild_id:
            where_clauses.append("guild_id = %s")
            params.append(guild_id)

        where_clause = " AND ".join(where_clauses)

        sql = f"""
            SELECT
                COUNT(*) as total_games,
                SUM(amount_bet) as total_bet,
                SUM(amount_won) as total_won,
                SUM(amount_lost) as total_lost,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'draw' OR result = 'push' THEN 1 ELSE 0 END) as draws,
                MAX(amount_won) as biggest_win
            FROM Games
            WHERE {where_clause}
        """
        # Note: This query uses aggregate functions, not SELECT *, so no changes needed

        try:
            result = self.execute_query(sql, params)
            if result and result[0][0] > 0:
                row = result[0]
                return {
                    'total_games': row[0],
                    'total_bet': row[1] or 0,
                    'total_won': row[2] or 0,
                    'total_lost': row[3] or 0,
                    'wins': row[4],
                    'draws': row[5],  # Add this
                    'losses': row[0] - row[4] - row[5],  # Update this to account for draws
                    'win_rate': (row[4] / row[0] * 100) if row[0] > 0 else 0,
                    'net_profit': (row[2] or 0) - (row[3] or 0),
                    'biggest_win': row[6] or 0
                }
            return {}
        except Exception as e:
            self.logger.error(f"Error getting {game_type} stats: {e}")
            return {}

    def get_leaderboard(self, guild_id: Optional[int] = None,
                        game_type: Optional[str] = None,
                        stat_type: str = 'net_profit',
                        limit: int = 10) -> List[Dict]:
        """Get leaderboard for various statistics"""
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
        # Note: This query uses aggregate functions and GROUP BY, not SELECT *, so no changes needed

        params.append(limit)

        try:
            results = self.execute_query(sql, params)
            return [
                {
                    'user_id': row[0],
                    'total_games': row[1],
                    'total_won': row[2] or 0,
                    'total_lost': row[3] or 0,
                    'net_profit': row[4] or 0,
                    'wins': row[5],
                    'win_rate': row[6] or 0
                }
                for row in results
            ] if results else []
        except Exception as e:
            self.logger.error(f"Error getting leaderboard: {e}")
            return []