from __future__ import annotations

from app.db import Database


class BalanceService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_pair_balances(self, pair_id: int):
        return await self.db.fetchall(
            """
            SELECT currency, COALESCE(SUM(signed_amount_minor), 0) AS balance_minor
            FROM transactions
            WHERE pair_id = ? AND status = 'accepted'
            GROUP BY currency
            ORDER BY currency
            """,
            (pair_id,),
        )
