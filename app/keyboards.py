from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.utils import SUPPORTED_CURRENCIES


MAIN_MENU_BUTTONS = (
    "Баланс",
    "Добавить трату",
    "История",
    "Отправить",
)

DESCRIPTION_CATEGORY_BUTTONS = (
    "Еда",
    "Транспорт",
    "Продукты",
    "Дом",
    "Развлечения",
    "Подарок",
    "Папачка",
    "Другое",
    "Без описания",
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for title in MAIN_MENU_BUTTONS:
        builder.add(KeyboardButton(text=title))
    builder.adjust(2, 2)
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


def description_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for title in DESCRIPTION_CATEGORY_BUTTONS:
        builder.add(KeyboardButton(text=title))
    builder.adjust(3, 3, 2, 1)
    builder.row(KeyboardButton(text="/cancel"))
    return builder.as_markup(resize_keyboard=True)


def draft_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Подтвердить", callback_data=f"draft:submit:{action}"),
        InlineKeyboardButton(text="Отменить", callback_data=f"draft:cancel:{action}"),
    )
    return builder.as_markup()


def switch_pair_keyboard(pairs, current_pair_id: int | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for pair in pairs:
        if pair["counterpart_first_name"]:
            label = pair["counterpart_first_name"]
        elif pair["counterpart_username"]:
            label = f"@{pair['counterpart_username']}"
        else:
            label = str(pair["counterpart_telegram_id"])

        if pair["id"] == current_pair_id:
            label = f"• {label}"

        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=f"pair:switch:{pair['id']}",
            )
        )
    return builder.as_markup()


def trust_keyboard(pair_id: int, current_enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    yes_text = "Да" + (" •" if current_enabled else "")
    no_text = "Нет" + ("" if current_enabled else " •")
    builder.row(
        InlineKeyboardButton(text=yes_text, callback_data=f"trust:set:{pair_id}:yes"),
        InlineKeyboardButton(text=no_text, callback_data=f"trust:set:{pair_id}:no"),
    )
    return builder.as_markup()
