from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import load_config
from app.db import Database
from app.handlers import setup_handlers
from app.services import build_services


async def build_dispatcher(db: Database) -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["services"] = build_services(db)
    setup_handlers(dispatcher)
    return dispatcher


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    db = Database(config.db_path)
    await db.initialize()

    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN is required to start polling")

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = await build_dispatcher(db)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    try:
        asyncio.run(run())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
