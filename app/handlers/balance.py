from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.keyboards import main_menu_keyboard
from app.services import ServiceContainer
from app.utils import format_minor_amount

router = Router()


@router.message(Command("balance"))
@router.message(F.text == "Баланс")
async def show_balance(message: Message, services: ServiceContainer) -> None:
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
    user1_name = services.users.display_name(
        {
            "first_name": pair_members["user1_first_name"],
            "username": pair_members["user1_username"],
            "telegram_id": pair_members["user1_telegram_id"],
        }
    )
    user2_name = services.users.display_name(
        {
            "first_name": pair_members["user2_first_name"],
            "username": pair_members["user2_username"],
            "telegram_id": pair_members["user2_telegram_id"],
        }
    )
    balances = await services.balances.get_pair_balances(pair["id"])
    if not balances:
        await message.answer(
            f"Текущая пара: {counterpart_name}\nБаланс нулевой.",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines: list[str] = [f"Текущая пара: {counterpart_name}"]
    for row in balances:
        balance_minor = row["balance_minor"]
        if balance_minor > 0:
            lines.append(f"{user2_name} должен {user1_name} {format_minor_amount(balance_minor, row['currency'])}")
        elif balance_minor < 0:
            lines.append(f"{user1_name} должен {user2_name} {format_minor_amount(abs(balance_minor), row['currency'])}")

    if not lines:
        await message.answer("Баланс нулевой.", reply_markup=main_menu_keyboard())
        return

    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())
