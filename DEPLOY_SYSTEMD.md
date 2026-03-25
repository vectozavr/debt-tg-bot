# Запуск бота как systemd-сервиса

Эта инструкция подходит для случая, когда у вас уже есть SSH-доступ к серверу и проект находится на удаленной машине.

## 1. Подключиться к серверу

```bash
ssh YOUR_USER@YOUR_SERVER_IP
```

## 2. Перейти в проект

```bash
cd /path/to/debt_bot
```

Проверьте путь:

```bash
pwd
```

## 3. Подготовить Python и зависимости

Если у вас уже есть рабочий `Python 3.11+`, который умеет `sqlite3`, создайте окружение и поставьте зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Проверка `sqlite3`:

```bash
.venv/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

Если здесь ошибка вида `No module named '_sqlite3'`, сначала нужно починить или заменить установленный Python.

## 4. Настроить `.env`

Если файла нет:

```bash
cp .env.example .env
nano .env
```

Минимум нужно указать:

```env
BOT_TOKEN=your_bot_token_here
DB_PATH=bot.db
```

## 5. Проверить ручной запуск

```bash
source .venv/bin/activate
python -m app.bot
```

Если бот стартовал без ошибок, остановите его через `Ctrl+C`.

## 6. Создать unit-файл systemd

Откройте файл:

```bash
sudo nano /etc/systemd/system/debt-bot.service
```

Пример содержимого:

```ini
[Unit]
Description=Debt Bot
After=network.target

[Service]
User=YOUR_USER
WorkingDirectory=/path/to/debt_bot
Environment=PYTHONUNBUFFERED=1
ExecStart=/path/to/debt_bot/.venv/bin/python -m app.bot
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Важно:

- `User` должен совпадать с пользователем, от которого лежит проект
- `WorkingDirectory` должен указывать на корень репозитория
- `ExecStart` должен указывать на реальный путь к `.venv/bin/python`

## 7. Перечитать конфиг systemd и запустить сервис

```bash
sudo systemctl daemon-reload
sudo systemctl enable debt-bot
sudo systemctl start debt-bot
```

## 8. Проверить статус

```bash
sudo systemctl status debt-bot --no-pager -l
```

Если все нормально, увидите `active (running)`.

## 9. Смотреть логи

Последние строки:

```bash
sudo journalctl -u debt-bot -n 50 --no-pager
```

В реальном времени:

```bash
sudo journalctl -u debt-bot -f
```

## 10. Полезные команды

Перезапуск:

```bash
sudo systemctl restart debt-bot
```

Остановить:

```bash
sudo systemctl stop debt-bot
```

Запустить снова:

```bash
sudo systemctl start debt-bot
```

Проверить автозапуск:

```bash
sudo systemctl is-enabled debt-bot
```

## 11. Обновление бота после изменений

```bash
cd /path/to/debt_bot
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart debt-bot
sudo systemctl status debt-bot --no-pager -l
```

## 12. Очистка базы на сервере

Если нужно сбросить все данные после тестов:

```bash
source .venv/bin/activate
python scripts/reset_db.py --yes
```

## Частые проблемы

### `status=203/EXEC`

Обычно это значит, что в `ExecStart` указан неверный путь.

Проверьте:

```bash
pwd
ls -l .venv/bin/python
sudo cat /etc/systemd/system/debt-bot.service
```

### `No module named '_sqlite3'`

Это проблема Python на сервере, а не бота. Нужно использовать Python, собранный с поддержкой SQLite.

### Логи пустые

Смотрите их через `sudo`:

```bash
sudo journalctl -u debt-bot -n 50 --no-pager
```
