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
            "Создайте пару командой /pair или присоединитесь по коду через /join.\n"
            "Если пар несколько, переключайте текущую через /switch.\n"
            "Валюту по умолчанию можно выбрать через /setcurrency, а автоподтверждение трат включается через /trust.\n"
            "Основные действия вынесены в меню, остальные команды смотрите в /help."
        ),
        reply_markup=main_menu_keyboard(),
    )
