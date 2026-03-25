from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.keyboards import main_menu_keyboard
from app.services import ServiceContainer
from app.utils import format_minor_amount, format_status, format_transaction_type

router = Router()


@router.message(Command("history"))
@router.message(F.text == "История")
async def show_history(message: Message, services: ServiceContainer) -> None:
    user = await services.users.ensure_user(message.from_user)
    pair = await services.pairs.get_selected_pair_for_user(user["id"])
    if not pair:
        await message.answer(
            "У вас нет выбранной пары. Используйте /pair, /join или /switch.",
            reply_markup=main_menu_keyboard(),
        )
        return

    pair_members = await services.pairs.get_pair_members(pair["id"])
    counterpart = services.pairs.get_counterparty_display_data(pair_members, user["id"])
    counterpart_name = services.users.display_name(counterpart)
    transactions = await services.transactions.list_recent_for_pair(pair["id"])
    if not transactions:
        await message.answer(
            f"Текущая пара: {counterpart_name}\nИстория пока пустая.",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines = [f"Текущая пара: {counterpart_name}", "", "Последние операции:"]
    for tx in transactions:
        author_name = services.users.display_name(
            {
                "first_name": tx["author_first_name"],
                "username": tx["author_username"],
                "telegram_id": None,
            }
        )
        lines.append(
            (
                f"#{tx['id']} | {format_transaction_type(tx['type'])} | "
                f"{format_minor_amount(tx['amount_minor'], tx['currency'])} | "
                f"{author_name} | {format_status(tx['status'])}\n"
                f"{tx['description'] or 'Без описания'}"
            )
        )

    await message.answer("\n\n".join(lines), reply_markup=main_menu_keyboard())
