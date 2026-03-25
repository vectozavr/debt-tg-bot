from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards import main_menu_keyboard, switch_pair_keyboard
from app.services import ServiceContainer

router = Router()


class PairStates(StatesGroup):
    waiting_for_invite_code = State()


@router.message(Command("pair"))
async def create_pair(message: Message, services: ServiceContainer) -> None:
    user = await services.users.ensure_user(message.from_user)
    try:
        pair = await services.pairs.create_pair(user["id"])
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=main_menu_keyboard())
        return

    await message.answer(
        f"Пара создана. Отправь этот код второму человеку: {pair['invite_code']}",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("join"))
async def join_pair_prompt(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    await services.users.ensure_user(message.from_user)
    await state.set_state(PairStates.waiting_for_invite_code)
    await message.answer("Введите invite code пары после команды /join.", reply_markup=main_menu_keyboard())


@router.message(PairStates.waiting_for_invite_code)
async def join_pair_submit(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    user = await services.users.ensure_user(message.from_user)
    invite_code = (message.text or "").strip().upper()

    try:
        pair = await services.pairs.join_pair(user["id"], invite_code)
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=main_menu_keyboard())
        return

    owner = await services.users.get_by_id(pair["user1_id"])
    await state.clear()
    await message.answer(
        f"Пара активирована. Теперь вы в паре с {services.users.display_name(owner)}.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("switch"))
async def switch_pair_prompt(message: Message, services: ServiceContainer) -> None:
    user = await services.users.ensure_user(message.from_user)
    pairs = await services.pairs.list_active_pairs_for_user(user["id"])
    if not pairs:
        await message.answer(
            "У вас пока нет активных пар. Используйте /pair или /join.",
            reply_markup=main_menu_keyboard(),
        )
        return

    current_pair = await services.pairs.get_selected_pair_for_user(user["id"])
    lines = ["Выберите текущую пару:"]
    for pair in pairs:
        label = services.users.display_name(
            {
                "first_name": pair["counterpart_first_name"],
                "username": pair["counterpart_username"],
                "telegram_id": pair["counterpart_telegram_id"],
            }
        )
        prefix = "• " if current_pair and pair["id"] == current_pair["id"] else ""
        lines.append(f"{prefix}{label}")

    await message.answer(
        "\n".join(lines),
        reply_markup=switch_pair_keyboard(pairs, current_pair["id"] if current_pair else None),
    )


@router.callback_query(F.data.startswith("pair:switch:"))
async def switch_pair_callback(
    callback: CallbackQuery,
    services: ServiceContainer,
) -> None:
    if not callback.data or not callback.from_user or not callback.message:
        await callback.answer()
        return

    _, action, raw_pair_id = callback.data.split(":")
    if action != "switch":
        await callback.answer()
        return

    try:
        pair_id = int(raw_pair_id)
    except ValueError:
        await callback.answer("Некорректный идентификатор пары", show_alert=True)
        return

    user = await services.users.ensure_user(callback.from_user)
    try:
        pair = await services.pairs.set_active_pair_for_user(user["id"], pair_id)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    members = await services.pairs.get_pair_members(pair["id"])
    counterpart = services.pairs.get_counterparty_display_data(members, user["id"])
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"Текущая пара переключена на {services.users.display_name(counterpart)}.",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer("Пара переключена")
