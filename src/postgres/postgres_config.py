"""Формирование конфигурации подключения к PostgreSQL.

Модуль извлекает параметры подключения из настроек приложения
и возвращает их в виде словаря для инициализации клиента БД.
"""

from __future__ import annotations

from src.settings import get_settings


def get_postgres_config() -> dict[str, str | int]:
    """Возвращает параметры подключения к Postgres из Settings.

    Fail-fast обеспечивается в get_settings(): если required env нет — падаем там.
    """
    s = get_settings()

    return {
        "user": s.POSTGRES_USER,
        "password": s.POSTGRES_PASSWORD,
        "database": s.POSTGRES_DB,
        "host": s.POSTGRES_HOST,
        "port": s.POSTGRES_PORT,
    }
