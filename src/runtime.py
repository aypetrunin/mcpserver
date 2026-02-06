"""Инициализация runtime-окружения приложения."""

import os
from pathlib import Path

from dotenv import load_dotenv


DEV_ENV_REL_PATH = Path("../deploy/dev.env")
"""Относительный путь к env-файлу для dev-окружения."""

PROD_ENV_REL_PATH = Path("../deploy/prod.env")
"""Относительный путь к env-файлу для prod-окружения."""


def init_runtime() -> None:
    """Загружает env-файл, если приложение запущено не в Docker."""
    is_docker = os.getenv("IS_DOCKER") == "1"
    if is_docker:
        return

    env = os.getenv("ENV", "dev").strip().lower()
    base_dir = Path(__file__).resolve().parents[1]

    env_rel_path = PROD_ENV_REL_PATH if env in ("prod", "production") else DEV_ENV_REL_PATH
    env_path = (base_dir / env_rel_path).resolve()

    if not env_path.exists():
        raise RuntimeError(f"Env file not found: {env_path}")

    load_dotenv(env_path, override=False)
