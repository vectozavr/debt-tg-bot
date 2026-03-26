from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards import (
    description_keyboard,
    draft_confirmation_keyboard,
    main_menu_keyboard,
    pending_transaction_keyboard,
)
from app.services import ServiceContainer
from app.utils import format_minor_amount, parse_amount_to_minor, uses_amount_formula

router = Router()


class ExpenseStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_description = State()


def _build_description(description: str, raw_amount: str) -> str:
    if not uses_amount_formula(raw_amount):
        return description
    if description:
        return f"{description}: {raw_amount}"
    return raw_amount


def _draft_preview(
    data: dict[str, str | int | bool],
    recipient_name: str,
    currency: str,
) -> str:
    resolved_flow = str(data["resolved_flow"])
    if resolved_flow == "send":
        title = "Проверьте отправку:"
        recipient_line = f"Кому уйдут деньги: {recipient_name}"
    else:
        title = "Проверьте запрос на трату:"
        recipient_line = f"Кому уйдет запрос: {recipient_name}"

    lines = [
        title,
        recipient_line,
        f"Сумма: {format_minor_amount(int(data['amount_minor']), currency)}",
        f"Описание: {data['description'] or 'Без описания'}",
    ]
    if data.get("converted_from_negative"):
        lines.append("")
        lines.append("Итог выражения оказался отрицательным, поэтому операция будет оформлена как отправка денег.")
    return "\n".join(lines)


async def _start_expense_flow(
    message: Message,
    state: FSMContext,
    services: ServiceContainer,
    *,
    flow: str,
) -> None:
    user = await services.users.ensure_user(message.from_user)
    pair = await services.pairs.get_selected_pair_for_user(user["id"])
    if not pair:
        await message.answer(
            "Нельзя создать операцию без выбранной пары. Используйте /pair, /join или /switch.",
            reply_markup=main_menu_keyboard(),
        )
        return

    currency = services.users.get_default_currency(user)
    await state.clear()
    await state.update_data(flow=flow)
    await state.set_state(ExpenseStates.waiting_for_amount)
    await message.answer(
        (
            f"Введите сумму в {currency}, например: 25.50\n"
            "Можно использовать математику: 35/2 + 12 - 5"
        ),
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("send"))
@router.message(F.text == "Отправить")
async def start_send_money(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    await _start_expense_flow(message, state, services, flow="send")


@router.message(Command(commands=["recieve", "receive"]))
@router.message(F.text == "Добавить трату")
@router.message(F.text == "Получить")
async def start_receive_money(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    await _start_expense_flow(message, state, services, flow="expense")


@router.message(ExpenseStates.waiting_for_amount)
async def expense_amount(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    flow = str(data.get("flow", "expense"))
    raw_amount = (message.text or "").strip()
    try:
        amount_minor = parse_amount_to_minor(
            raw_amount,
            allow_negative=flow == "expense",
            allow_zero=flow == "expense",
        )
    except ValueError as exc:
        await message.answer(str(exc))
        return

    resolved_flow = flow
    converted_from_negative = False
    if flow == "expense" and amount_minor < 0:
        resolved_flow = "send"
        converted_from_negative = True
        amount_minor = abs(amount_minor)

    await state.update_data(
        amount_minor=amount_minor,
        resolved_flow=resolved_flow,
        converted_from_negative=converted_from_negative,
        raw_amount=raw_amount,
    )
    await state.set_state(ExpenseStates.waiting_for_description)
    await message.answer(
        "Введите описание или выберите категорию.",
        reply_markup=description_keyboard(),
    )


@router.message(ExpenseStates.waiting_for_description)
async def expense_description(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    description = (message.text or "").strip()
    if not description:
        await message.answer("Можно ввести текст или выбрать категорию с клавиатуры.")
        return

    if description == "Без описания":
        description = ""

    data = await state.get_data()
    full_description = _build_description(description, str(data.get("raw_amount", "")))
    await state.update_data(description=full_description)
    data = await state.get_data()
    user = await services.users.ensure_user(message.from_user)
    pair = await services.pairs.get_selected_pair_for_user(user["id"])
    if not pair:
        await state.clear()
        await message.answer(
            "У вас нет выбранной пары. Используйте /switch.",
            reply_markup=main_menu_keyboard(),
        )
        return

    pair_members = await services.pairs.get_pair_members(pair["id"])
    counterpart = services.pairs.get_counterparty_display_data(pair_members, user["id"])
    counterpart_name = services.users.display_name(counterpart)
    currency = services.users.get_default_currency(user)
    resolved_flow = str(data.get("resolved_flow", "expense"))
    action = "send_money" if resolved_flow == "send" else "receive_money"
    await message.answer(
        _draft_preview(data, counterpart_name, currency),
        reply_markup=draft_confirmation_keyboard(action),
    )


@router.callback_query(F.data == "draft:submit:receive_money")
async def submit_receive_money(
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

    currency = services.users.get_default_currency(user)
    tx = await services.transactions.create_expense(
        pair_row=pair,
        currency=currency,
        created_by_user_id=user["id"],
        counterparty_user_id=counterparty_id,
        amount_minor=int(data["amount_minor"]),
        description=str(data["description"]),
    )

    if services.pairs.is_counterparty_trusted(pair, user["id"]):
        tx = await services.transactions.accept(tx["id"], counterparty_id)
        await _notify_counterparty_autoaccepted_expense(bot=bot, services=services, tx=tx)
        author_message = "Трата автоматически подтверждена, потому что в этой паре включено доверие."
    else:
        await _notify_counterparty_pending_expense(bot=bot, services=services, tx=tx)
        author_message = "Запрос отправлен второй стороне."

    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(author_message, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "draft:submit:send_money")
async def submit_send_money(
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

    currency = services.users.get_default_currency(user)
    tx = await services.transactions.create_settlement_accepted(
        pair_row=pair,
        currency=currency,
        created_by_user_id=user["id"],
        counterparty_user_id=counterparty_id,
        amount_minor=int(data["amount_minor"]),
        description=str(data["description"]),
    )
    await _notify_counterparty_transfer(bot=bot, services=services, tx=tx)
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Перевод зафиксирован и вторая сторона уведомлена.",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


async def _notify_counterparty_pending_expense(bot: Bot, services: ServiceContainer, tx) -> None:
    author = await services.users.get_by_id(tx["created_by_user_id"])
    counterparty = await services.users.get_by_id(tx["counterparty_user_id"])
    author_name = services.users.display_name(author)
    await bot.send_message(
        counterparty["telegram_id"],
        (
            f"{author_name} добавил(а) трату.\n"
            f"Сумма: {format_minor_amount(tx['amount_minor'], tx['currency'])}\n"
            f"Описание: {tx['description'] or 'Без описания'}"
        ),
        reply_markup=pending_transaction_keyboard(tx["id"]),
    )


async def _notify_counterparty_autoaccepted_expense(bot: Bot, services: ServiceContainer, tx) -> None:
    author = await services.users.get_by_id(tx["created_by_user_id"])
    counterparty = await services.users.get_by_id(tx["counterparty_user_id"])
    author_name = services.users.display_name(author)
    await bot.send_message(
        counterparty["telegram_id"],
        (
            f"{author_name} добавил(а) трату.\n"
            f"Сумма: {format_minor_amount(tx['amount_minor'], tx['currency'])}\n"
            f"Описание: {tx['description'] or 'Без описания'}\n"
            "Операция подтверждена автоматически, потому что для этой пары включено доверие."
        ),
        reply_markup=main_menu_keyboard(),
    )


async def _notify_counterparty_transfer(bot: Bot, services: ServiceContainer, tx) -> None:
    author = await services.users.get_by_id(tx["created_by_user_id"])
    counterparty = await services.users.get_by_id(tx["counterparty_user_id"])
    author_name = services.users.display_name(author)
    await bot.send_message(
        counterparty["telegram_id"],
        (
            f"{author_name} отправил(а) вам {format_minor_amount(tx['amount_minor'], tx['currency'])}.\n"
            f"Описание: {tx['description'] or 'Без описания'}"
        ),
        reply_markup=main_menu_keyboard(),
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
