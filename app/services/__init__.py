from __future__ import annotations

from dataclasses import dataclass

from app.db import Database
from app.services.balances import BalanceService
from app.services.pairs import PairService
from app.services.transactions import TransactionService
from app.services.users import UserService


@dataclass(slots=True)
class ServiceContainer:
    users: UserService
    pairs: PairService
    transactions: TransactionService
    balances: BalanceService


def build_services(db: Database) -> ServiceContainer:
    users = UserService(db)
    pairs = PairService(db)
    transactions = TransactionService(db)
    balances = BalanceService(db)
    return ServiceContainer(
        users=users,
        pairs=pairs,
        transactions=transactions,
        balances=balances,
    )
