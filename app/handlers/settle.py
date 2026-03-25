from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards import draft_confirmation_keyboard, main_menu_keyboard, pending_transaction_keyboard
from app.services import ServiceContainer
from app.utils import format_minor_amount, parse_amount_to_minor

router = Router()


class SettlementStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_description = State()


def _draft_preview(data: dict[str, str | int], currency: str) -> str:
    return (
        "Проверьте погашение:\n"
        f"Сумма: {format_minor_amount(int(data['amount_minor']), currency)}\n"
        f"Комментарий: {data['description']}"
    )


@router.message(Command("settle"))
@router.message(F.text == "Погашение")
async def start_settlement(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    user = await services.users.ensure_user(message.from_user)
    pair = await services.pairs.get_selected_pair_for_user(user["id"])
    if not pair:
        await message.answer(
            "У вас нет выбранной пары. Используйте /pair, /join или /switch.",
            reply_markup=main_menu_keyboard(),
        )
        return

    currency = services.users.get_default_currency(user)
    await state.clear()
    await state.set_state(SettlementStates.waiting_for_amount)
    await message.answer(
        (
            f"Введите сумму погашения в {currency}, например: 25.50\n"
            "Можно использовать математику: 35/2 + 12 - 5"
        ),
        reply_markup=main_menu_keyboard(),
    )


@router.message(SettlementStates.waiting_for_amount)
async def settlement_amount(message: Message, state: FSMContext) -> None:
    try:
        amount_minor = parse_amount_to_minor(message.text or "")
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await state.update_data(amount_minor=amount_minor)
    await state.set_state(SettlementStates.waiting_for_description)
    await message.answer("Введите комментарий, например: перевел через банк.")


@router.message(SettlementStates.waiting_for_description)
async def settlement_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    if not description:
        await message.answer("Комментарий не должен быть пустым.")
        return

    await state.update_data(description=description)
    data = await state.get_data()
    user = await services.users.ensure_user(message.from_user)
    currency = services.users.get_default_currency(user)
    await message.answer(
        _draft_preview(data, currency),
        reply_markup=draft_confirmation_keyboard("settlement"),
    )


@router.callback_query(F.data == "draft:submit:settlement")
async def submit_settlement(
    callback: CallbackQuery,
    state: FSMContext,
    services: ServiceContainer,
    bot: Bot,
) -> None:
    if not callback.message or not callback.from_user:
        await callback.answer()
        return

    data = await state.get_data()
    if not data:
        await callback.answer("Черновик не найден", show_alert=True)
        return

    user = await services.users.ensure_user(callback.from_user)
    pair = await services.pairs.get_selected_pair_for_user(user["id"])
    if not pair:
        await state.clear()
        await callback.message.answer(
            "У вас нет выбранной пары. Используйте /switch.",
            reply_markup=main_menu_keyboard(),
        )
        await callback.answer()
        return

    counterparty_id = await services.pairs.get_counterparty_id(pair, user["id"])
    if not counterparty_id:
        await callback.answer("Пара еще не активна", show_alert=True)
        return

    tx = await services.transactions.create_settlement(
        pair_row=pair,
        currency=services.users.get_default_currency(user),
        created_by_user_id=user["id"],
        counterparty_user_id=counterparty_id,
        amount_minor=int(data["amount_minor"]),
        description=str(data["description"]),
    )
    await _notify_counterparty_pending_settlement(
        bot=bot,
        services=services,
        tx=tx,
    )
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Запрос отправлен второй стороне.", reply_markup=main_menu_keyboard())
    await callback.answer()


async def _notify_counterparty_pending_settlement(
    *,
    bot: Bot,
    services: ServiceContainer,
    tx,
) -> None:
    author_name = services.users.display_name(
        {
            "first_name": tx["author_first_name"],
            "username": tx["author_username"],
            "telegram_id": tx["author_telegram_id"],
        }
    )
    try:
        await bot.send_message(
            chat_id=tx["counterparty_telegram_id"],
            text=(
                f"{author_name} добавил(а) погашение и ждет вашего подтверждения.\n"
                f"Сумма: {format_minor_amount(tx['amount_minor'], tx['currency'])}\n"
                f"Описание: {tx['description'] or 'Без описания'}"
            ),
            reply_markup=pending_transaction_keyboard(tx["id"]),
        )
    except Exception:
        return
