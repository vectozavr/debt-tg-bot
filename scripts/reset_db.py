from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import load_config
from app.db import Database


TABLES_TO_CLEAR = (
    "transactions",
    "pairs",
    "users",
)


async def reset_database(db_path: Path) -> None:
    db = Database(db_path)
    await db.initialize()

    async with db.connection() as connection:
        for table_name in TABLES_TO_CLEAR:
            await connection.execute(f"DELETE FROM {table_name}")

        await connection.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('users', 'pairs', 'transactions')"
        )
        await connection.commit()


def parse_args() -> argparse.Namespace:
    config = load_config()
    parser = argparse.ArgumentParser(
        description="Очистить все таблицы SQLite базы debt bot."
    )
    parser.add_argument(
        "--db",
        default=str(config.db_path),
        help="Путь к SQLite базе. По умолчанию используется DB_PATH из .env.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Очистить базу без интерактивного подтверждения.",
    )
    return parser.parse_args()


def confirm(db_path: Path) -> None:
    answer = input(f"Очистить все данные в {db_path}? [y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        raise SystemExit("Отменено.")


def main() -> None:
    args = parse_args()
    db_path = Path(args.db).expanduser()
    if not args.yes:
        confirm(db_path)

    asyncio.run(reset_database(db_path))
    print(f"База очищена: {db_path}")


if __name__ == "__main__":
    main()
