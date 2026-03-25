from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aiosqlite


CREATE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pairs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_id INTEGER NOT NULL,
        user2_id INTEGER,
        invite_code TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user1_id) REFERENCES users(id),
        FOREIGN KEY(user2_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair_id INTEGER NOT NULL,
        currency TEXT NOT NULL,
        created_by_user_id INTEGER NOT NULL,
        counterparty_user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        amount_minor INTEGER NOT NULL,
        signed_amount_minor INTEGER NOT NULL,
        description TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        confirmed_at TEXT,
        FOREIGN KEY(pair_id) REFERENCES pairs(id),
        FOREIGN KEY(created_by_user_id) REFERENCES users(id),
        FOREIGN KEY(counterparty_user_id) REFERENCES users(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_pairs_invite_code ON pairs(invite_code)",
    """
    CREATE INDEX IF NOT EXISTS idx_transactions_pair_status_currency
    ON transactions(pair_id, status, currency)
    """,
)


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    @asynccontextmanager
    async def connection(self):
        connection = await aiosqlite.connect(self.path)
        connection.row_factory = aiosqlite.Row
        await connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            await connection.close()

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with self.connection() as connection:
            for statement in CREATE_STATEMENTS:
                await connection.execute(statement)
            await self._migrate_users_active_pair(connection)
            await self._migrate_user_default_currency(connection)
            await self._migrate_pair_trust(connection)
            await connection.commit()

    async def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        async with self.connection() as connection:
            async with connection.execute(query, params) as cursor:
                return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        async with self.connection() as connection:
            async with connection.execute(query, params) as cursor:
                return await cursor.fetchall()

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        async with self.connection() as connection:
            cursor = await connection.execute(query, params)
            await connection.commit()
            return cursor.lastrowid

    async def execute_many(self, statements: list[tuple[str, tuple[Any, ...]]]) -> None:
        async with self.connection() as connection:
            for query, params in statements:
                await connection.execute(query, params)
            await connection.commit()

    async def _migrate_users_active_pair(self, connection: aiosqlite.Connection) -> None:
        async with connection.execute("PRAGMA table_info(users)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}

        if "active_pair_id" not in columns:
            await connection.execute(
                "ALTER TABLE users ADD COLUMN active_pair_id INTEGER"
            )

        await connection.execute(
            """
            UPDATE users
            SET active_pair_id = (
                SELECT p.id
                FROM pairs p
                WHERE p.status = 'active'
                  AND (p.user1_id = users.id OR p.user2_id = users.id)
                ORDER BY p.id
                LIMIT 1
            )
            WHERE active_pair_id IS NULL
            """
        )

    async def _migrate_user_default_currency(self, connection: aiosqlite.Connection) -> None:
        async with connection.execute("PRAGMA table_info(users)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}

        if "default_currency" not in columns:
            await connection.execute(
                "ALTER TABLE users ADD COLUMN default_currency TEXT NOT NULL DEFAULT 'RUB'"
            )

        await connection.execute(
            """
            UPDATE users
            SET default_currency = 'RUB'
            WHERE default_currency IS NULL OR default_currency = ''
            """
        )

    async def _migrate_pair_trust(self, connection: aiosqlite.Connection) -> None:
        async with connection.execute("PRAGMA table_info(pairs)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}

        if "trust_user1_to_user2" not in columns:
            await connection.execute(
                "ALTER TABLE pairs ADD COLUMN trust_user1_to_user2 INTEGER NOT NULL DEFAULT 0"
            )
        if "trust_user2_to_user1" not in columns:
            await connection.execute(
                "ALTER TABLE pairs ADD COLUMN trust_user2_to_user1 INTEGER NOT NULL DEFAULT 0"
            )
