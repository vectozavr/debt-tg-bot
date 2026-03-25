from __future__ import annotations

from app.db import Database
from app.utils import generate_invite_code, now_iso


class PairService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_active_pair_for_user(self, user_id: int):
        return await self.db.fetchone(
            """
            SELECT * FROM pairs
            WHERE status = 'active' AND (user1_id = ? OR user2_id = ?)
            LIMIT 1
            """,
            (user_id, user_id),
        )

    async def get_pending_pair_by_owner(self, user_id: int):
        return await self.db.fetchone(
            """
            SELECT * FROM pairs
            WHERE status = 'pending' AND user1_id = ? AND user2_id IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        )

    async def get_by_id(self, pair_id: int):
        return await self.db.fetchone(
            "SELECT * FROM pairs WHERE id = ?",
            (pair_id,),
        )

    async def get_by_invite_code(self, invite_code: str):
        return await self.db.fetchone(
            "SELECT * FROM pairs WHERE invite_code = ?",
            (invite_code,),
        )

    async def create_pair(self, user_id: int):
        active_pair = await self.get_active_pair_for_user(user_id)
        if active_pair:
            raise ValueError("У вас уже есть активная пара")

        pending_pair = await self.get_pending_pair_by_owner(user_id)
        if pending_pair:
            return pending_pair

        invite_code = await self._generate_unique_code()
        pair_id = await self.db.execute(
            """
            INSERT INTO pairs (user1_id, user2_id, invite_code, status, created_at)
            VALUES (?, NULL, ?, 'pending', ?)
            """,
            (user_id, invite_code, now_iso()),
        )
        return await self.get_by_id(pair_id)

    async def join_pair(self, user_id: int, invite_code: str):
        active_pair = await self.get_active_pair_for_user(user_id)
        if active_pair:
            raise ValueError("У вас уже есть активная пара")

        pair = await self.get_by_invite_code(invite_code)
        if not pair:
            raise ValueError("Код пары не найден")
        if pair["status"] != "pending":
            raise ValueError("Эта пара уже активирована")
        if pair["user1_id"] == user_id:
            raise ValueError("Нельзя создать пару с самим собой")

        owner_active_pair = await self.get_active_pair_for_user(pair["user1_id"])
        if owner_active_pair:
            raise ValueError("У создателя уже есть активная пара")

        await self.db.execute(
            """
            UPDATE pairs
            SET user2_id = ?, status = 'active'
            WHERE id = ?
            """,
            (user_id, pair["id"]),
        )
        return await self.get_by_id(pair["id"])

    async def get_pair_members(self, pair_id: int):
        return await self.db.fetchone(
            """
            SELECT
                p.*,
                u1.telegram_id AS user1_telegram_id,
                u1.username AS user1_username,
                u1.first_name AS user1_first_name,
                u2.telegram_id AS user2_telegram_id,
                u2.username AS user2_username,
                u2.first_name AS user2_first_name
            FROM pairs p
            JOIN users u1 ON u1.id = p.user1_id
            LEFT JOIN users u2 ON u2.id = p.user2_id
            WHERE p.id = ?
            """,
            (pair_id,),
        )

    async def get_counterparty_id(self, pair_row, user_id: int) -> int | None:
        if pair_row["user1_id"] == user_id:
            return pair_row["user2_id"]
        if pair_row["user2_id"] == user_id:
            return pair_row["user1_id"]
        return None

    async def _generate_unique_code(self) -> str:
        while True:
            code = generate_invite_code()
            existing = await self.get_by_invite_code(code)
            if not existing:
                return code
