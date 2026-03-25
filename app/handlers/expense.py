from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards import currency_keyboard, draft_confirmation_keyboard, main_menu_keyboard, pending_transaction_keyboard
from app.services import ServiceContainer
from app.utils import format_minor_amount, parse_amount_to_minor, validate_currency

router = Router()


class ExpenseStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_description = State()
    waiting_for_currency = State()


def _draft_preview(data: dict[str, str | int]) -> str:
    return (
        "Проверьте трату:\n"
        f"Сумма: {format_minor_amount(int(data['amount_minor']), str(data['currency']))}\n"
        f"Описание: {data['description']}"
    )


async def _start_expense_flow(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    user = await services.users.ensure_user(message.from_user)
    pair = await services.pairs.get_active_pair_for_user(user["id"])
    if not pair:
        await message.answer("Нельзя добавить расход без активной пары.", reply_markup=main_menu_keyboard())
        return

    await state.clear()
    await state.set_state(ExpenseStates.waiting_for_amount)
    await message.answer("Введите сумму, например: 25.50", reply_markup=main_menu_keyboard())


@router.message(Command("send"))
@router.message(Command(commands=["recieve", "receive"]))
@router.message(F.text == "Добавить трату")
async def start_expense(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    await _start_expense_flow(message, state, services)


@router.message(ExpenseStates.waiting_for_amount)
async def expense_amount(message: Message, state: FSMContext) -> None:
    try:
        amount_minor = parse_amount_to_minor(message.text or "")
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await state.update_data(amount_minor=amount_minor)
    await state.set_state(ExpenseStates.waiting_for_description)
    await message.answer("Введите описание траты.")


@router.message(ExpenseStates.waiting_for_description)
async def expense_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    if not description:
        await message.answer("Описание не должно быть пустым.")
        return

    await state.update_data(description=description)
    await state.set_state(ExpenseStates.waiting_for_currency)
    await message.answer("Выберите валюту.", reply_markup=currency_keyboard())


@router.message(ExpenseStates.waiting_for_currency)
async def expense_currency(message: Message, state: FSMContext) -> None:
    try:
        currency = validate_currency(message.text or "")
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=currency_keyboard())
        return

    await state.update_data(currency=currency)
    data = await state.get_data()
    await message.answer(
        _draft_preview(data),
        reply_markup=draft_confirmation_keyboard("expense"),
    )


@router.callback_query(F.data == "draft:submit:expense")
async def submit_expense(
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
    pair = await services.pairs.get_active_pair_for_user(user["id"])
    if not pair:
        await state.clear()
        await callback.message.answer("У вас нет активной пары.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return

    counterparty_id = await services.pairs.get_counterparty_id(pair, user["id"])
    if not counterparty_id:
        await callback.answer("Пара еще не активна", show_alert=True)
        return

    tx = await services.transactions.create_expense(
        pair_row=pair,
        currency=str(data["currency"]),
        created_by_user_id=user["id"],
        counterparty_user_id=counterparty_id,
        amount_minor=int(data["amount_minor"]),
        description=str(data["description"]),
    )
    counterparty = await services.users.get_by_id(counterparty_id)
    await _notify_counterparty(
        bot=bot,
        services=services,
        tx=tx,
        action_label="добавил(а) трату",
    )
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Запрос отправлен второй стороне.", reply_markup=main_menu_keyboard())
    await callback.answer()


async def _notify_counterparty(bot: Bot, services: ServiceContainer, tx, action_label: str) -> None:
    author = await services.users.get_by_id(tx["created_by_user_id"])
    counterparty = await services.users.get_by_id(tx["counterparty_user_id"])
    author_name = services.users.display_name(author)
    await bot.send_message(
        counterparty["telegram_id"],
        (
            f"{author_name} {action_label}.\n"
            f"Сумма: {format_minor_amount(tx['amount_minor'], tx['currency'])}\n"
            f"Описание: {tx['description'] or 'Без описания'}"
        ),
        reply_markup=pending_transaction_keyboard(tx["id"]),
    )


@router.callback_query(F.data.startswith("tx:"))
async def handle_transaction_callback(
    callback: CallbackQuery,
    services: ServiceContainer,
    bot: Bot,
) -> None:
    if not callback.data or not callback.from_user or not callback.message:
        await callback.answer()
        return

    _, action, raw_tx_id = callback.data.split(":")
    try:
        tx_id = int(raw_tx_id)
    except ValueError:
        await callback.answer("Некорректный идентификатор", show_alert=True)
        return

    user = await services.users.ensure_user(callback.from_user)
    try:
        if action == "accept":
            tx = await services.transactions.accept(tx_id, user["id"])
            user_message = "Операция подтверждена."
            author_message = "Ваша операция подтверждена."
        elif action == "reject":
            tx = await services.transactions.reject(tx_id, user["id"])
            user_message = "Операция отклонена."
            author_message = "Ваша операция отклонена."
        else:
            await callback.answer("Неизвестное действие", show_alert=True)
            return
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(user_message, reply_markup=main_menu_keyboard())
    author = await services.users.get_by_id(tx["created_by_user_id"])
    await bot.send_message(author["telegram_id"], author_message, reply_markup=main_menu_keyboard())
    await callback.answer()
