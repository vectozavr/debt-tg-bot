from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards import main_menu_keyboard
from app.services import ServiceContainer

router = Router()


@router.message(CommandStart())
async def start_command(message: Message, services: ServiceContainer) -> None:
    await services.users.ensure_user(message.from_user)
    await message.answer(
        (
            "Привет! Это бот для учета долгов между двумя людьми.\n\n"
            "Создайте пару или введите код пары, затем добавляйте траты, "
            "подтверждайте их и смотрите баланс."
        ),
        reply_markup=main_menu_keyboard(),
    )
