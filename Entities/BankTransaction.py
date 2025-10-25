from typing import Optional, Union
from datetime import datetime
from Entities.BaseEntity import BaseEntity


class BankTransaction(BaseEntity):
    """
    BankTransaction entity representing a bank deposit/withdraw/interest transaction.
    """

    def __init__(
            self,
            id: Optional[int] = None,
            user_id: int = 0,
            guild_id: int = 0,
            transaction_type: str = 'deposit',
            amount: int = 0,
            fee: int = 0,
            balance_before: int = 0,
            balance_after: int = 0,
            timestamp: Union[str, datetime, None] = None
    ):
        self._id = id
        self._user_id = int(user_id) if user_id else 0
        self._guild_id = int(guild_id) if guild_id else 0
        self._transaction_type = str(transaction_type) if transaction_type else 'deposit'
        self._amount = int(amount) if amount else 0
        self._fee = int(fee) if fee else 0
        self._balance_before = int(balance_before) if balance_before else 0
        self._balance_after = int(balance_after) if balance_after else 0
        self._timestamp = timestamp

    @property
    def id(self) -> Optional[int]:
        """Transaction ID"""
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def user_id(self) -> int:
        """Discord user ID"""
        return self._user_id

    @user_id.setter
    def user_id(self, value):
        self._user_id = int(value) if value else 0

    @property
    def guild_id(self) -> int:
        """Discord guild ID where transaction occurred"""
        return self._guild_id

    @guild_id.setter
    def guild_id(self, value):
        self._guild_id = int(value) if value else 0

    @property
    def transaction_type(self) -> str:
        """Type of transaction: deposit, withdraw, or interest"""
        return self._transaction_type

    @transaction_type.setter
    def transaction_type(self, value):
        self._transaction_type = str(value) if value else 'deposit'

    @property
    def amount(self) -> int:
        """Amount of currency transacted"""
        return self._amount

    @amount.setter
    def amount(self, value):
        self._amount = int(value) if value else 0

    @property
    def fee(self) -> int:
        """Fee charged for transaction"""
        return self._fee

    @fee.setter
    def fee(self, value):
        self._fee = int(value) if value else 0

    @property
    def balance_before(self) -> int:
        """Bank balance before transaction"""
        return self._balance_before

    @balance_before.setter
    def balance_before(self, value):
        self._balance_before = int(value) if value else 0

    @property
    def balance_after(self) -> int:
        """Bank balance after transaction"""
        return self._balance_after

    @balance_after.setter
    def balance_after(self, value):
        self._balance_after = int(value) if value else 0

    @property
    def timestamp(self) -> Union[str, datetime, None]:
        """When the transaction occurred"""
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value

    def __repr__(self):
        return (f"BankTransaction(id={self.id}, user_id={self.user_id}, "
                f"guild_id={self.guild_id}, type={self.transaction_type}, "
                f"amount={self.amount}, fee={self.fee}, "
                f"balance_before={self.balance_before}, balance_after={self.balance_after}, "
                f"timestamp={self.timestamp})")
