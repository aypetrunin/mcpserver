"""Инициализация и управление пулом подключений PostgreSQL.

Содержит функции для создания, получения и закрытия
глобального асинхронного пула `asyncpg.Pool`.
"""

from __future__ import annotations

import asyncpg

from src.settings import get_settings

from .postgres_config import get_postgres_config


_pool: asyncpg.Pool | None = None


async def init_pg_pool() -> asyncpg.Pool:
    """Инициализирует пул Postgres.

    Вызывается один раз на старте процесса.
    """
    global _pool
    if _pool is not None:
        return _pool

    s = get_settings()

    min_size = s.PG_POOL_MIN
    max_size = s.PG_POOL_MAX
    acquire_timeout = float(s.PG_CONNECT_TIMEOUT_S)
    statement_timeout_ms = s.PG_STATEMENT_TIMEOUT_MS

    pg_config = get_postgres_config()

    async def _init_conn(conn: asyncpg.Connection) -> None:
        """Инициализирует параметры соединения Postgres."""
        await conn.execute(f"SET statement_timeout = {statement_timeout_ms}")

    _pool = await asyncpg.create_pool(
        **pg_config,
        min_size=min_size,
        max_size=max_size,
        timeout=acquire_timeout,
        init=_init_conn,
    )
    return _pool


def get_pg_pool() -> asyncpg.Pool:
    """Возвращает инициализированный пул Postgres.

    Raises:
        RuntimeError: Если пул ещё не инициализирован.
    """
    if _pool is None:
        raise RuntimeError(
            "Postgres pool not initialized. Call init_pg_pool() on startup."
        )
    return _pool


async def close_pg_pool() -> None:
    """Закрывает пул Postgres (если он был инициализирован)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
