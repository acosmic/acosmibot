from typing import List, Optional, Tuple
from Dao.BaseDao import BaseDao
from Entities.BankTransaction import BankTransaction


class BankTransactionDao(BaseDao):
    """Data Access Object for BankTransaction operations"""

    def __init__(self):
        super().__init__(BankTransaction, "BankTransactions")
        self.create_table()

    def create_table(self) -> bool:
        """
        Create the BankTransactions table if it doesn't exist.

        Returns:
            bool: True if successful, False otherwise
        """
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS BankTransactions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                transaction_type ENUM('deposit', 'withdraw', 'interest') NOT NULL,
                amount INT NOT NULL,
                fee INT DEFAULT 0,
                balance_before INT NOT NULL,
                balance_after INT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_transactions (user_id, timestamp DESC),
                INDEX idx_guild_transactions (guild_id, timestamp DESC),
                INDEX idx_timestamp (timestamp DESC)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        return self.create_table_if_not_exists(create_table_sql)

    def add_transaction(self, transaction: BankTransaction, commit: bool = True) -> bool:
        """
        Add a new bank transaction to the database.

        Args:
            transaction (BankTransaction): Transaction to add
            commit (bool): Whether to commit immediately (default True)

        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            INSERT INTO BankTransactions (
                user_id, guild_id, transaction_type, amount, fee,
                balance_before, balance_after, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            transaction.user_id,
            transaction.guild_id,
            transaction.transaction_type,
            transaction.amount,
            transaction.fee,
            transaction.balance_before,
            transaction.balance_after,
            transaction.timestamp
        )

        try:
            self.execute_query(sql, values, commit=commit)
            self.logger.info(f"Added bank transaction for user {transaction.user_id}: {transaction.transaction_type} {transaction.amount}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding bank transaction: {e}")
            return False

    def get_user_transactions(self, user_id: int, limit: int = 10) -> List[BankTransaction]:
        """
        Get recent transactions for a user.

        Args:
            user_id (int): Discord user ID
            limit (int): Maximum number of transactions to return

        Returns:
            List[BankTransaction]: List of transactions
        """
        sql = """
            SELECT id, user_id, guild_id, transaction_type, amount, fee,
                   balance_before, balance_after, timestamp
            FROM BankTransactions
            WHERE user_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """

        try:
            results = self.execute_query(sql, (user_id, limit))
            transactions = []

            if results:
                for row in results:
                    transaction = BankTransaction(
                        id=row[0],
                        user_id=row[1],
                        guild_id=row[2],
                        transaction_type=row[3],
                        amount=row[4],
                        fee=row[5],
                        balance_before=row[6],
                        balance_after=row[7],
                        timestamp=row[8]
                    )
                    transactions.append(transaction)

            return transactions
        except Exception as e:
            self.logger.error(f"Error getting user transactions for {user_id}: {e}")
            return []

    def get_guild_transactions(self, guild_id: int, limit: int = 10) -> List[BankTransaction]:
        """
        Get recent transactions for a guild.

        Args:
            guild_id (int): Discord guild ID
            limit (int): Maximum number of transactions to return

        Returns:
            List[BankTransaction]: List of transactions
        """
        sql = """
            SELECT id, user_id, guild_id, transaction_type, amount, fee,
                   balance_before, balance_after, timestamp
            FROM BankTransactions
            WHERE guild_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """

        try:
            results = self.execute_query(sql, (guild_id, limit))
            transactions = []

            if results:
                for row in results:
                    transaction = BankTransaction(
                        id=row[0],
                        user_id=row[1],
                        guild_id=row[2],
                        transaction_type=row[3],
                        amount=row[4],
                        fee=row[5],
                        balance_before=row[6],
                        balance_after=row[7],
                        timestamp=row[8]
                    )
                    transactions.append(transaction)

            return transactions
        except Exception as e:
            self.logger.error(f"Error getting guild transactions for {guild_id}: {e}")
            return []

    def get_transaction_stats(self, user_id: int) -> dict:
        """
        Get transaction statistics for a user.

        Args:
            user_id (int): Discord user ID

        Returns:
            dict: Statistics including total deposits, withdrawals, and fees paid
        """
        sql = """
            SELECT
                transaction_type,
                COUNT(*) as count,
                SUM(amount) as total_amount,
                SUM(fee) as total_fees
            FROM BankTransactions
            WHERE user_id = %s
            GROUP BY transaction_type
        """

        try:
            results = self.execute_query(sql, (user_id,))
            stats = {
                'total_deposits': 0,
                'total_withdrawals': 0,
                'total_interest': 0,
                'total_fees_paid': 0,
                'deposit_count': 0,
                'withdraw_count': 0,
                'interest_count': 0
            }

            if results:
                for row in results:
                    transaction_type = row[0]
                    count = row[1]
                    total_amount = row[2] if row[2] else 0
                    total_fees = row[3] if row[3] else 0

                    if transaction_type == 'deposit':
                        stats['total_deposits'] = total_amount
                        stats['deposit_count'] = count
                    elif transaction_type == 'withdraw':
                        stats['total_withdrawals'] = total_amount
                        stats['withdraw_count'] = count
                    elif transaction_type == 'interest':
                        stats['total_interest'] = total_amount
                        stats['interest_count'] = count

                    stats['total_fees_paid'] += total_fees

            return stats
        except Exception as e:
            self.logger.error(f"Error getting transaction stats for user {user_id}: {e}")
            return {
                'total_deposits': 0,
                'total_withdrawals': 0,
                'total_interest': 0,
                'total_fees_paid': 0,
                'deposit_count': 0,
                'withdraw_count': 0,
                'interest_count': 0
            }

    def get_daily_transfer_total(self, user_id: int) -> int:
        """
        Get total amount transferred (deposited + withdrawn) today for a user.

        Args:
            user_id (int): Discord user ID

        Returns:
            int: Total amount transferred today
        """
        sql = """
            SELECT COALESCE(SUM(amount), 0)
            FROM BankTransactions
            WHERE user_id = %s
            AND DATE(timestamp) = CURDATE()
            AND transaction_type IN ('deposit', 'withdraw')
        """

        try:
            result = self.execute_query(sql, (user_id,))
            return int(result[0][0]) if result and result[0] else 0
        except Exception as e:
            self.logger.error(f"Error getting daily transfer total for user {user_id}: {e}")
            return 0
