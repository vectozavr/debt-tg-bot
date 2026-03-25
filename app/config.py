from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Config:
    bot_token: str | None
    db_path: Path


def load_config() -> Config:
    load_dotenv()
    db_path = Path(os.getenv("DB_PATH", "bot.db")).expanduser()
    return Config(
        bot_token=os.getenv("BOT_TOKEN"),
        db_path=db_path,
    )
