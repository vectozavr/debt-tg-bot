from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards import main_menu_keyboard

router = Router()


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Нет активного сценария.", reply_markup=main_menu_keyboard())
        return

    await state.clear()
    await message.answer("Текущий сценарий отменен.", reply_markup=main_menu_keyboard())
@router.callback_query(F.data.startswith("draft:cancel:"))
async def cancel_draft(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Сценарий отменен.", reply_markup=main_menu_keyboard())
    await callback.answer()
