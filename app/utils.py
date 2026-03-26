from __future__ import annotations

import ast
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


def _evaluate_expression(node: ast.AST) -> Decimal:
    if isinstance(node, ast.Expression):
        return _evaluate_expression(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Decimal(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        operand = _evaluate_expression(node.operand)
        return operand if isinstance(node.op, ast.UAdd) else -operand
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left = _evaluate_expression(node.left)
        right = _evaluate_expression(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if right == 0:
            raise ValueError("Деление на ноль недопустимо")
        return left / right
    raise ValueError("Допустимы только числа, скобки и операции + - * /")


def evaluate_amount_expression(raw_amount: str) -> Decimal:
    normalized = raw_amount.strip().replace(",", ".")
    if not normalized:
        raise ValueError("Введите сумму")

    try:
        parsed = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Не удалось распознать выражение. Пример: 35/2 + 12 - 5") from exc

    try:
        return _evaluate_expression(parsed)
    except InvalidOperation as exc:
        raise ValueError("Не удалось распознать выражение. Пример: 35/2 + 12 - 5") from exc


def uses_amount_formula(raw_amount: str) -> bool:
    normalized = raw_amount.strip().replace(",", ".")
    if not normalized:
        return False

    try:
        parsed = ast.parse(normalized, mode="eval")
    except SyntaxError:
        return False

    body = parsed.body
    if isinstance(body, ast.Constant) and isinstance(body.value, (int, float)):
        return False
    if (
        isinstance(body, ast.UnaryOp)
        and isinstance(body.op, (ast.UAdd, ast.USub))
        and isinstance(body.operand, ast.Constant)
        and isinstance(body.operand.value, (int, float))
    ):
        return False
    return True


def parse_amount_to_minor(
    raw_amount: str,
    *,
    allow_negative: bool = False,
    allow_zero: bool = False,
) -> int:
    amount = evaluate_amount_expression(raw_amount)
    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    amount_minor = int(quantized * 100)

    if not allow_negative and amount_minor < 0:
        raise ValueError("Сумма не должна быть отрицательной")
    if not allow_zero and amount_minor == 0:
        raise ValueError("Сумма не должна быть равна нулю")
    if not allow_negative and amount_minor <= 0:
        raise ValueError("Сумма должна быть больше нуля")

    return amount_minor


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
