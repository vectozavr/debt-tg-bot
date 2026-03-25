from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.keyboards import main_menu_keyboard

router = Router()


HELP_TEXT = (
    "Команды бота:\n"
    "/start - регистрация и главное меню\n"
    "/help - показать это сообщение\n"
    "/pair - создать пару и получить invite code\n"
    "/join - ввести invite code и присоединиться к паре\n"
    "/switch - выбрать текущую пару\n"
    "/balance - показать баланс\n"
    "/history - показать последние операции\n"
    "/send - добавить трату\n"
    "/recieve - добавить трату\n"
    "/settle - добавить погашение\n"
    "/cancel - отменить текущий сценарий\n\n"
    "В меню оставлены только частые действия. Создание пары, ввод кода, "
    "погашение и справка доступны как команды.\n\n"
    "Логика простая: траты и погашения создаются как запросы, вторая сторона "
    "подтверждает или отклоняет их."
)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard())
