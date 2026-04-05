from __future__ import annotations

import os
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
DB_PATH = APP_ROOT / "transporte.db"
EXCEL_ORIGEM = APP_ROOT / "seed_transporte_local.xlsm"
ENV_PATH = APP_ROOT / "app_notas.env"


def _load_local_env(env_path: Path = ENV_PATH) -> None:
    if not env_path.exists():
        return

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)
    except OSError:
        pass


def _env(nome: str, padrao: str = "") -> str:
    valor = os.getenv(nome, "").strip()
    return valor or padrao


def _env_int(nome: str, padrao: int) -> int:
    try:
        return int(_env(nome, str(padrao)))
    except ValueError:
        return padrao


_load_local_env()


OPENWEATHER_API_KEY = _env("APP_NOTAS_OPENWEATHER_API_KEY")
TELEGRAM_TOKEN = _env("APP_NOTAS_TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = _env("APP_NOTAS_TELEGRAM_CHAT_ID")

BACKUP_DRIVE_PATH = Path(_env("APP_NOTAS_BACKUP_PATH", r"G:\Meu Drive\backupsistemas")).expanduser()
MAX_BACKUPS = _env_int("APP_NOTAS_MAX_BACKUPS", 50)
MAX_LOCAL_BACKUPS = _env_int("APP_NOTAS_MAX_LOCAL_BACKUPS", MAX_BACKUPS)
SQLITE_BUSY_TIMEOUT_MS = _env_int("APP_NOTAS_SQLITE_BUSY_TIMEOUT_MS", 5000)
LOG_LEVEL = _env("APP_NOTAS_LOG_LEVEL", "INFO").upper()
LOG_DIR = APP_ROOT / "logs"
LOG_PATH = LOG_DIR / "app_notas.log"
