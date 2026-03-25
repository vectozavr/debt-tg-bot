from __future__ import annotations

from aiogram import Dispatcher

from app.handlers.balance import router as balance_router
from app.handlers.common import router as common_router
from app.handlers.expense import router as expense_router
from app.handlers.help import router as help_router
from app.handlers.history import router as history_router
from app.handlers.pair import router as pair_router
from app.handlers.settle import router as settle_router
from app.handlers.start import router as start_router


def setup_handlers(dispatcher: Dispatcher) -> None:
    dispatcher.include_router(common_router)
    dispatcher.include_router(start_router)
    dispatcher.include_router(help_router)
    dispatcher.include_router(pair_router)
    dispatcher.include_router(balance_router)
    dispatcher.include_router(expense_router)
    dispatcher.include_router(history_router)
    dispatcher.include_router(settle_router)
