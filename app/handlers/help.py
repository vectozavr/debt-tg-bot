from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.keyboards import main_menu_keyboard

router = Router()


HELP_TEXT = (
    "Команды бота:\n"
    "/start - регистрация и главное меню\n"
    "/pair - создать пару или ввести код\n"
    "/balance - показать баланс\n"
    "/history - показать последние операции\n"
    "/send - добавить трату\n"
    "/recieve - добавить трату\n"
    "/settle - добавить погашение\n"
    "/cancel - отменить текущий сценарий\n\n"
    "Логика простая: траты и погашения создаются как запросы, "
    "вторая сторона подтверждает или отклоняет их."
)


@router.message(Command("help"))
@router.message(F.text == "Помощь")
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard())
