# Debt Bot MVP

Простой Telegram-бот на `aiogram 3`, который помогает двум людям вести учет взаимных трат и долгов без реальных платежей внутри бота.

## Что умеет бот

- регистрировать пользователей через `/start`
- создавать пару и подключать второго участника по invite code
- хранить траты и погашения в SQLite
- отправлять второй стороне запрос на подтверждение или отклонение
- показывать историю операций
- считать баланс по каждой валюте отдельно

## Функции MVP

- несколько пар на пользователя с выбором текущей через `/switch`
- только пары из двух человек
- валюты: `SAR`, `USD`, `AED`, `LARI`, `LIRA`, `RUB`
- траты и погашения создаются как `pending`, затем переходят в `accepted` или `rejected`
- подтвержденные операции не редактируются

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка `.env`

Создайте `.env` на основе `.env.example`:

```env
BOT_TOKEN=your_bot_token_here
DB_PATH=bot.db
```

## Запуск

```bash
python3 -m app.bot
```

Если `BOT_TOKEN` не задан, инициализация БД и импорт проекта работают, но long polling не стартует.

## Очистка базы после тестов

```bash
python3 scripts/reset_db.py
```

Без подтверждения:

```bash
python3 scripts/reset_db.py --yes
```

Для другой базы:

```bash
python3 scripts/reset_db.py --db /tmp/test_bot.db --yes
```

## Команды

- `/start`
- `/help`
- `/pair`
- `/join`
- `/switch`
- `/balance`
- `/history`
- `/send`
- `/recieve`
- `/settle`
- `/cancel`

## Логика баланса

Баланс считается относительно `user1` пары.

- `expense` от `user1` дает `+amount`
- `expense` от `user2` дает `-amount`
- `settlement` от `user1` дает `+amount`
- `settlement` от `user2` дает `-amount`

Дальше бот суммирует только операции со статусом `accepted`.

- если сумма больше нуля, `user2` должен `user1`
- если сумма меньше нуля, `user1` должен `user2`
- если сумма равна нулю, баланс нулевой

## Ограничения MVP

- без webhook
- без Docker
- без внешней БД
- без OCR
- без групп и пар на 3+ участников
- без платежных шлюзов и реальных переводов денег
