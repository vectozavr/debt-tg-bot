from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards import currency_keyboard, main_menu_keyboard, trust_keyboard
from app.services import ServiceContainer
from app.utils import validate_currency

router = Router()


class SettingsStates(StatesGroup):
    waiting_for_currency = State()


@router.message(Command("setcurrency"))
async def set_currency_prompt(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    user = await services.users.ensure_user(message.from_user)
    current_currency = services.users.get_default_currency(user)
    await state.clear()
    await state.set_state(SettingsStates.waiting_for_currency)
    await message.answer(
        (
            f"Текущая валюта по умолчанию: {current_currency}\n"
            "Выберите новую валюту на клавиатуре или введите ее вручную."
        ),
        reply_markup=currency_keyboard(),
    )


@router.message(SettingsStates.waiting_for_currency)
async def set_currency_submit(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    user = await services.users.ensure_user(message.from_user)
    try:
        currency = validate_currency(message.text or "")
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=currency_keyboard())
        return

    await services.users.set_default_currency(user["id"], currency)
    await state.clear()
    await message.answer(
        f"Валюта по умолчанию установлена: {currency}",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("trust"))
async def trust_prompt(message: Message, services: ServiceContainer) -> None:
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

    if pair["user1_id"] == user["id"]:
        current_enabled = bool(pair["trust_user1_to_user2"])
    else:
        current_enabled = bool(pair["trust_user2_to_user1"])

    await message.answer(
        f"Доверять вашей паре с {counterpart_name}?",
        reply_markup=trust_keyboard(pair["id"], current_enabled),
    )


@router.callback_query(F.data.startswith("trust:set:"))
async def trust_submit(
    callback: CallbackQuery,
    services: ServiceContainer,
) -> None:
    if not callback.data or not callback.from_user or not callback.message:
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    _, action, raw_pair_id, raw_enabled = parts
    if action != "set":
        await callback.answer()
        return

    try:
        pair_id = int(raw_pair_id)
    except ValueError:
        await callback.answer("Некорректный идентификатор пары", show_alert=True)
        return

    enabled = raw_enabled == "yes"
    user = await services.users.ensure_user(callback.from_user)
    try:
        pair = await services.pairs.set_trust_for_user(pair_id, user["id"], enabled)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    pair_members = await services.pairs.get_pair_members(pair["id"])
    counterpart = services.pairs.get_counterparty_display_data(pair_members, user["id"])
    counterpart_name = services.users.display_name(counterpart)

    if pair["user1_id"] == user["id"]:
        current_enabled = bool(pair["trust_user1_to_user2"])
    else:
        current_enabled = bool(pair["trust_user2_to_user1"])

    await callback.message.edit_reply_markup(
        reply_markup=trust_keyboard(pair["id"], current_enabled),
    )
    if enabled:
        await callback.message.answer(
            f"Теперь траты от {counterpart_name} будут подтверждаться автоматически.",
            reply_markup=main_menu_keyboard(),
        )
        await callback.answer("Доверие включено")
        return

    await callback.message.answer(
        f"Автоподтверждение трат от {counterpart_name} выключено.",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer("Доверие выключено")
