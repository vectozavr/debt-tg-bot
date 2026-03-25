from __future__ import annotations

from app.db import Database
from app.utils import now_iso


class TransactionService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create_expense(
        self,
        *,
        pair_row,
        currency: str,
        created_by_user_id: int,
        counterparty_user_id: int,
        amount_minor: int,
        description: str,
    ):
        signed_amount_minor = self._calculate_signed_amount(
            pair_row=pair_row,
            created_by_user_id=created_by_user_id,
            amount_minor=amount_minor,
            tx_type="expense",
        )
        tx_id = await self._create_transaction(
            pair_id=pair_row["id"],
            currency=currency,
            created_by_user_id=created_by_user_id,
            counterparty_user_id=counterparty_user_id,
            tx_type="expense",
            amount_minor=amount_minor,
            signed_amount_minor=signed_amount_minor,
            description=description,
        )
        return await self.get_by_id(tx_id)

    async def create_settlement(
        self,
        *,
        pair_row,
        currency: str,
        created_by_user_id: int,
        counterparty_user_id: int,
        amount_minor: int,
        description: str,
    ):
        signed_amount_minor = self._calculate_signed_amount(
            pair_row=pair_row,
            created_by_user_id=created_by_user_id,
            amount_minor=amount_minor,
            tx_type="settlement",
        )
        tx_id = await self._create_transaction(
            pair_id=pair_row["id"],
            currency=currency,
            created_by_user_id=created_by_user_id,
            counterparty_user_id=counterparty_user_id,
            tx_type="settlement",
            amount_minor=amount_minor,
            signed_amount_minor=signed_amount_minor,
            description=description,
        )
        return await self.get_by_id(tx_id)

    async def get_by_id(self, tx_id: int):
        return await self.db.fetchone(
            """
            SELECT
                t.*,
                author.telegram_id AS author_telegram_id,
                author.first_name AS author_first_name,
                author.username AS author_username,
                counterparty.telegram_id AS counterparty_telegram_id,
                counterparty.first_name AS counterparty_first_name,
                counterparty.username AS counterparty_username
            FROM transactions t
            JOIN users author ON author.id = t.created_by_user_id
            JOIN users counterparty ON counterparty.id = t.counterparty_user_id
            WHERE t.id = ?
            """,
            (tx_id,),
        )

    async def list_recent_for_pair(self, pair_id: int, limit: int = 10):
        return await self.db.fetchall(
            """
            SELECT
                t.*,
                author.first_name AS author_first_name,
                author.username AS author_username
            FROM transactions t
            JOIN users author ON author.id = t.created_by_user_id
            WHERE t.pair_id = ?
            ORDER BY t.id DESC
            LIMIT ?
            """,
            (pair_id, limit),
        )

    async def accept(self, tx_id: int, acting_user_id: int):
        tx = await self.get_by_id(tx_id)
        if not tx:
            raise ValueError("Операция не найдена")
        if tx["created_by_user_id"] == acting_user_id:
            raise ValueError("Нельзя подтверждать свою же операцию")
        if tx["counterparty_user_id"] != acting_user_id:
            raise ValueError("Эта операция не для вас")
        if tx["status"] != "pending":
            raise ValueError("Операция уже завершена")

        await self.db.execute(
            """
            UPDATE transactions
            SET status = 'accepted', confirmed_at = ?
            WHERE id = ?
            """,
            (now_iso(), tx_id),
        )
        return await self.get_by_id(tx_id)

    async def reject(self, tx_id: int, acting_user_id: int):
        tx = await self.get_by_id(tx_id)
        if not tx:
            raise ValueError("Операция не найдена")
        if tx["created_by_user_id"] == acting_user_id:
            raise ValueError("Нельзя подтверждать свою же операцию")
        if tx["counterparty_user_id"] != acting_user_id:
            raise ValueError("Эта операция не для вас")
        if tx["status"] != "pending":
            raise ValueError("Операция уже завершена")

        await self.db.execute(
            """
            UPDATE transactions
            SET status = 'rejected', confirmed_at = ?
            WHERE id = ?
            """,
            (now_iso(), tx_id),
        )
        return await self.get_by_id(tx_id)

    async def _create_transaction(
        self,
        *,
        pair_id: int,
        currency: str,
        created_by_user_id: int,
        counterparty_user_id: int,
        tx_type: str,
        amount_minor: int,
        signed_amount_minor: int,
        description: str,
    ) -> int:
        return await self.db.execute(
            """
            INSERT INTO transactions (
                pair_id,
                currency,
                created_by_user_id,
                counterparty_user_id,
                type,
                amount_minor,
                signed_amount_minor,
                description,
                status,
                created_at,
                confirmed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, NULL)
            """,
            (
                pair_id,
                currency,
                created_by_user_id,
                counterparty_user_id,
                tx_type,
                amount_minor,
                signed_amount_minor,
                description,
                now_iso(),
            ),
        )

    @staticmethod
    def _calculate_signed_amount(
        *,
        pair_row,
        created_by_user_id: int,
        amount_minor: int,
        tx_type: str,
    ) -> int:
        is_user1 = pair_row["user1_id"] == created_by_user_id
        if tx_type == "expense":
            return amount_minor if is_user1 else -amount_minor
        if tx_type == "settlement":
            return amount_minor if is_user1 else -amount_minor
        raise ValueError("Неизвестный тип операции")
