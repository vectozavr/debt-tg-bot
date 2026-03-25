from __future__ import annotations

from app.db import Database
from app.utils import generate_invite_code, now_iso


class PairService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_selected_pair_for_user(self, user_id: int):
        user = await self.db.fetchone(
            "SELECT active_pair_id FROM users WHERE id = ?",
            (user_id,),
        )
        if not user:
            return None

        active_pair_id = user["active_pair_id"]
        if active_pair_id is not None:
            pair = await self.db.fetchone(
                """
                SELECT * FROM pairs
                WHERE id = ? AND status = 'active' AND (user1_id = ? OR user2_id = ?)
                """,
                (active_pair_id, user_id, user_id),
            )
            if pair:
                return pair

        fallback_pair = await self.db.fetchone(
            """
            SELECT * FROM pairs
            WHERE status = 'active' AND (user1_id = ? OR user2_id = ?)
            ORDER BY id
            LIMIT 1
            """,
            (user_id, user_id),
        )
        if fallback_pair:
            await self.set_active_pair_for_user(user_id, fallback_pair["id"])
        return fallback_pair

    async def get_active_pair_for_user(self, user_id: int):
        return await self.get_selected_pair_for_user(user_id)

    async def list_active_pairs_for_user(self, user_id: int):
        return await self.db.fetchall(
            """
            SELECT
                p.*,
                CASE
                    WHEN p.user1_id = ? THEN u2.id
                    ELSE u1.id
                END AS counterpart_id,
                CASE
                    WHEN p.user1_id = ? THEN u2.telegram_id
                    ELSE u1.telegram_id
                END AS counterpart_telegram_id,
                CASE
                    WHEN p.user1_id = ? THEN u2.username
                    ELSE u1.username
                END AS counterpart_username,
                CASE
                    WHEN p.user1_id = ? THEN u2.first_name
                    ELSE u1.first_name
                END AS counterpart_first_name
            FROM pairs p
            JOIN users u1 ON u1.id = p.user1_id
            JOIN users u2 ON u2.id = p.user2_id
            WHERE p.status = 'active' AND (p.user1_id = ? OR p.user2_id = ?)
            ORDER BY p.id DESC
            """,
            (user_id, user_id, user_id, user_id, user_id, user_id),
        )

    async def set_active_pair_for_user(self, user_id: int, pair_id: int):
        pair = await self.db.fetchone(
            """
            SELECT * FROM pairs
            WHERE id = ? AND status = 'active' AND (user1_id = ? OR user2_id = ?)
            """,
            (pair_id, user_id, user_id),
        )
        if not pair:
            raise ValueError("Эта пара вам недоступна")

        await self.db.execute(
            "UPDATE users SET active_pair_id = ? WHERE id = ?",
            (pair_id, user_id),
        )
        return pair

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
        pair = await self.get_by_invite_code(invite_code)
        if not pair:
            raise ValueError("Код пары не найден")
        if pair["status"] != "pending":
            raise ValueError("Эта пара уже активирована")
        if pair["user1_id"] == user_id:
            raise ValueError("Нельзя создать пару с самим собой")

        await self.db.execute(
            """
            UPDATE pairs
            SET user2_id = ?, status = 'active'
            WHERE id = ?
            """,
            (user_id, pair["id"]),
        )
        await self._set_active_pair_if_missing(user_id, pair["id"])
        await self._set_active_pair_if_missing(pair["user1_id"], pair["id"])
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

    def get_counterparty_display_data(self, pair_members, user_id: int) -> dict[str, int | str | None]:
        if pair_members["user1_id"] == user_id:
            return {
                "id": pair_members["user2_id"],
                "telegram_id": pair_members["user2_telegram_id"],
                "username": pair_members["user2_username"],
                "first_name": pair_members["user2_first_name"],
            }
        return {
            "id": pair_members["user1_id"],
            "telegram_id": pair_members["user1_telegram_id"],
            "username": pair_members["user1_username"],
            "first_name": pair_members["user1_first_name"],
        }

    async def _set_active_pair_if_missing(self, user_id: int, pair_id: int) -> None:
        user = await self.db.fetchone(
            "SELECT active_pair_id FROM users WHERE id = ?",
            (user_id,),
        )
        if user and user["active_pair_id"] is None:
            await self.db.execute(
                "UPDATE users SET active_pair_id = ? WHERE id = ?",
                (pair_id, user_id),
            )

    async def _generate_unique_code(self) -> str:
        while True:
            code = generate_invite_code()
            existing = await self.get_by_invite_code(code)
            if not existing:
                return code
