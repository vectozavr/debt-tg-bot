from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.keyboards import main_menu_keyboard
from app.services import ServiceContainer

router = Router()


class PairStates(StatesGroup):
    waiting_for_invite_code = State()


@router.message(Command("pair"))
async def pair_command(message: Message) -> None:
    await message.answer(
        "Используйте кнопки: «Создать пару» или «Ввести код пары».",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == "Создать пару")
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
@router.message(F.text == "Ввести код пары")
async def join_pair_prompt(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    await services.users.ensure_user(message.from_user)
    await state.set_state(PairStates.waiting_for_invite_code)
    await message.answer("Введите invite code пары.", reply_markup=main_menu_keyboard())


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
