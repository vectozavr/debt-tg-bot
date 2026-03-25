from __future__ import annotations

from aiogram.types import User as TelegramUser

from app.db import Database
from app.utils import validate_currency
from app.utils import now_iso


class UserService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def ensure_user(self, tg_user: TelegramUser):
        existing = await self.get_by_telegram_id(tg_user.id)
        if existing:
            await self.db.execute(
                """
                UPDATE users
                SET username = ?, first_name = ?
                WHERE telegram_id = ?
                """,
                (tg_user.username, tg_user.first_name, tg_user.id),
            )
            return await self.get_by_telegram_id(tg_user.id)

        await self.db.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (tg_user.id, tg_user.username, tg_user.first_name, now_iso()),
        )
        return await self.get_by_telegram_id(tg_user.id)

    async def get_by_telegram_id(self, telegram_id: int):
        return await self.db.fetchone(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )

    async def get_by_id(self, user_id: int):
        return await self.db.fetchone(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        )

    async def set_default_currency(self, user_id: int, currency: str) -> None:
        validated_currency = validate_currency(currency)
        await self.db.execute(
            "UPDATE users SET default_currency = ? WHERE id = ?",
            (validated_currency, user_id),
        )

    def get_default_currency(self, user_row) -> str:
        return user_row["default_currency"] or "RUB"

    @staticmethod
    def display_name(user_row) -> str:
        if not user_row:
            return "Неизвестный пользователь"
        if user_row["first_name"]:
            return user_row["first_name"]
        if user_row["username"]:
            return f"@{user_row['username']}"
        return str(user_row["telegram_id"])
