from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.utils import SUPPORTED_CURRENCIES


MAIN_MENU_BUTTONS = (
    "Создать пару",
    "Ввести код пары",
    "Баланс",
    "Добавить трату",
    "История",
    "Погашение",
    "Помощь",
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for title in MAIN_MENU_BUTTONS:
        builder.add(KeyboardButton(text=title))
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def currency_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for currency in SUPPORTED_CURRENCIES:
        builder.add(KeyboardButton(text=currency))
    builder.adjust(3, 3)
    builder.row(KeyboardButton(text="/cancel"))
    return builder.as_markup(resize_keyboard=True)


def pending_transaction_keyboard(tx_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Подтвердить", callback_data=f"tx:accept:{tx_id}"),
        InlineKeyboardButton(text="Отклонить", callback_data=f"tx:reject:{tx_id}"),
    )
    return builder.as_markup()


def draft_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Подтвердить", callback_data=f"draft:submit:{action}"),
        InlineKeyboardButton(text="Отменить", callback_data=f"draft:cancel:{action}"),
    )
    return builder.as_markup()
