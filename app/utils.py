from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from random import SystemRandom
from string import ascii_uppercase, digits


SUPPORTED_CURRENCIES = ("SAR", "USD", "AED", "LARI", "LIRA", "RUB")
PAIR_CODE_ALPHABET = ascii_uppercase + digits
PAIR_CODE_LENGTH = 6
_random = SystemRandom()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_invite_code() -> str:
    return "".join(_random.choice(PAIR_CODE_ALPHABET) for _ in range(PAIR_CODE_LENGTH))


def parse_amount_to_minor(raw_amount: str) -> int:
    normalized = raw_amount.strip().replace(",", ".")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Не удалось распознать сумму. Используйте формат 25.50") from exc

    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")

    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(quantized * 100)


def format_minor_amount(amount_minor: int, currency: str) -> str:
    amount = Decimal(amount_minor) / Decimal("100")
    return f"{amount:.2f} {currency}"


def validate_currency(raw_currency: str) -> str:
    currency = raw_currency.strip().upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(
            "Поддерживаемые валюты: " + ", ".join(SUPPORTED_CURRENCIES)
        )
    return currency


def format_status(status: str) -> str:
    mapping = {
        "pending": "pending",
        "accepted": "accepted",
        "rejected": "rejected",
    }
    return mapping.get(status, status)


def format_transaction_type(tx_type: str) -> str:
    mapping = {
        "expense": "Трата",
        "settlement": "Погашение",
    }
    return mapping.get(tx_type, tx_type)
