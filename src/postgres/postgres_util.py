"""Модуль вспомогательных утилит работы с Postgres.

Раньше здесь был psycopg2:
- на каждый вызов создавалось новое соединение
- это блокировало event loop в async-сервисе
- и было медленнее/тяжелее

Теперь:
- используется asyncpg pool (создаётся 1 раз на старте процесса)
- каждое обращение к БД берёт соединение из пула на время операции
- у запросов есть таймауты (чтобы не зависать навсегда)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from asyncpg import Record

from .db_pool import get_pg_pool


logger = logging.getLogger(__name__)

PG_QUERY_TIMEOUT_S = float(os.getenv("PG_QUERY_TIMEOUT_S", "5"))


async def select_key(channel_id: int) -> dict[str, Any]:
    """Выбирает уникальные ключи из view для данного канала.

    Возвращает:
    {
        "body_parts": "...",
        "indications_key": "...",
        "contraindications_key": "..."
    }

    Если данных нет — возвращает {}.
    """
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        row: Record | None = await conn.fetchrow(
            """
            SELECT body_parts, indications_key, contraindications_key
            FROM view_channel_services_keys
            WHERE channel_id = $1;
            """,
            channel_id,
            timeout=PG_QUERY_TIMEOUT_S,
        )

        if row is None:
            return {}

        return {
            "body_parts": row["body_parts"],
            "indications_key": row["indications_key"],
            "contraindications_key": row["contraindications_key"],
        }


async def create_or_replace_view() -> None:
    """Создаёт или заменяет VIEW view_channel_services_keys."""
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE OR REPLACE VIEW view_channel_services_keys AS
            ...
            """,
            timeout=PG_QUERY_TIMEOUT_S,
        )


async def create_product_service_view() -> None:
    """Создаёт или заменяет VIEW product_service_view."""
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DROP VIEW IF EXISTS product_service_view;", timeout=PG_QUERY_TIMEOUT_S
            )
            await conn.execute(
                """
                CREATE VIEW product_service_view AS
                ...
                """,
                timeout=PG_QUERY_TIMEOUT_S,
            )


async def read_secondary_article_by_primary(
    primary_article: str,
    primary_channel: int,
    secondary_channel: int,
) -> str | None:
    """Возвращает article связанного (secondary) товара для primary_article."""
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            SELECT p_secondary.article
            FROM products p_primary
            LEFT JOIN products p_secondary
              ON p_primary.product_name = p_secondary.product_name
             AND p_secondary.channel_id = $1
            WHERE p_primary.channel_id = $2
              AND p_primary.article = $3
            LIMIT 1;
            """,
            secondary_channel,
            primary_channel,
            primary_article,
            timeout=PG_QUERY_TIMEOUT_S,
        )


async def get_product_name_for_id(product_id: str) -> str | None:
    """Возвращает название продукта по его article/id.

    Если продукта нет — возвращает ``None``.
    """
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            SELECT p.product_name
            FROM products p
            WHERE p.article = $1
            """,
            product_id,
            timeout=PG_QUERY_TIMEOUT_S,
        )


def _run_cli() -> None:
    """Локальный запуск для ручной проверки."""
    import asyncio

    from ..runtime import init_runtime
    from .db_pool import close_pg_pool, init_pg_pool

    init_runtime()

    async def _demo() -> None:
        await init_pg_pool()
        try:
            result = await select_key(channel_id=1)
            logger.info("%s", result)
        finally:
            await close_pg_pool()

    asyncio.run(_demo())


if __name__ == "__main__":
    _run_cli()

# cd /home/copilot_superuser/petrunin/zena
# uv run python -m mcpserver.src.postgres.postgres_util
