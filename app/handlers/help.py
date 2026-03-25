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
    "/setcurrency - выбрать валюту по умолчанию для новых операций\n"
    "/trust - включить или выключить автоподтверждение трат для текущей пары\n"
    "/balance - показать баланс\n"
    "/history - показать последние операции\n"
    "/send - отправить деньги второй стороне без подтверждения\n"
    "/recieve - добавить трату, которую вторая сторона подтверждает\n"
    "/settle - добавить погашение\n"
    "/cancel - отменить текущий сценарий\n\n"
    "В меню оставлены только частые действия. Создание пары, ввод кода, "
    "погашение и справка доступны как команды.\n\n"
    "Логика простая: «Добавить трату» создает запрос на деньги с подтверждением, "
    "а «Отправить» сразу фиксирует перевод и только уведомляет вторую сторону. "
    "Сумму можно вводить как выражение, например: 35/2 + 12 - 5. "
    "Если в «Добавить трату» итог ушел в минус, бот автоматически оформит это как отправку денег."
)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard())
