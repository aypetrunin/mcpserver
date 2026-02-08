"""Модуль создания вспомогательных VIEW в Postgres (asyncpg + pool).

Зачем этот файл:
- В базе есть "представления" (VIEW) — это как виртуальные таблицы.
- Их нужно иногда создавать или обновлять (CREATE OR REPLACE VIEW).

Почему теперь asyncpg, а не psycopg2:
- psycopg2 — синхронный и блокирует event loop (плохо для async сервиса).
- asyncpg — асинхронный и хорошо работает в asyncio.
- pool позволяет не создавать новое соединение на каждый вызов.
"""

from __future__ import annotations

import os

from src.runtime import init_runtime

from .db_pool import close_pg_pool, get_pg_pool, init_pg_pool


PG_DDL_TIMEOUT_S = float(os.getenv("PG_DDL_TIMEOUT_S", "15"))


async def create_view_channel_services_keys() -> None:
    """Создаёт или заменяет представление view_channel_services_keys в базе."""
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE OR REPLACE VIEW view_channel_services_keys AS
            SELECT
                ch.id AS channel_id,
                (
                    SELECT string_agg('"' || bp || '"', ', ')
                    FROM (
                        SELECT DISTINCT TRIM(b) AS bp
                        FROM (
                            SELECT regexp_split_to_table(s.body_parts, '[,]+') AS b
                            FROM services s WHERE s.channel_id = ch.id AND s.body_parts IS NOT NULL
                        ) AS sub WHERE b <> ''
                    ) uniq
                ) AS body_parts,
                (
                    SELECT string_agg('"' || ik || '"', ', ')
                    FROM (
                        SELECT DISTINCT TRIM(i) AS ik
                        FROM (
                            SELECT regexp_split_to_table(s.indications_key, '[,]+') AS i
                            FROM services s WHERE s.channel_id = ch.id AND s.indications_key IS NOT NULL
                        ) AS sub WHERE i <> ''
                    ) uniq
                ) AS indications_key,
                (
                    SELECT string_agg('"' || ck || '"', ', ')
                    FROM (
                        SELECT DISTINCT TRIM(c) AS ck
                        FROM (
                            SELECT regexp_split_to_table(s.contraindications_key, '[,]+') AS c
                            FROM services s WHERE s.channel_id = ch.id AND s.contraindications_key IS NOT NULL
                        ) AS sub WHERE c <> ''
                    ) uniq
                ) AS contraindications_key
            FROM channel ch
            WHERE ch.url_googlesheet_data IS NOT NULL AND TRIM(ch.url_googlesheet_data) <> ''
            ORDER BY ch.id;
            """,
            timeout=PG_DDL_TIMEOUT_S,
        )


async def create_product_service_view() -> None:
    """Создаёт или заменяет представление product_service_view в базе."""
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DROP VIEW IF EXISTS product_service_view;", timeout=PG_DDL_TIMEOUT_S
            )
            await conn.execute(
                """
                CREATE VIEW product_service_view AS
                SELECT
                    p.channel_id,
                    p.product_id as id,
                    p.article AS product_id,
                    p.product_name AS product_name,
                    p.product_full_name AS product_full_name,
                    p.description AS product_description,
                    p.time_minutes AS duration,
                    p.price_min,
                    p.price_max,
                    s.services_name,
                    s.description AS service_description,
                    s.indications,
                    s.contraindications,
                    s.pre_session_instructions,
                    s.indications_key,
                    s.contraindications_key,
                    s.mult_score_boosting,
                    p.product_full_name AS product_search,
                    s.body_parts
                FROM products p
                LEFT JOIN products_services ps ON p.article = ps.article_id
                LEFT JOIN services s ON ps.service_id = s.id;
                """,
                timeout=PG_DDL_TIMEOUT_S,
            )


async def create_all_views() -> None:
    """Создаёт все необходимые VIEW."""
    await create_view_channel_services_keys()
    await create_product_service_view()


def _run_cli() -> None:
    """Запуск обновления VIEW из консоли."""
    import asyncio
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    async def _demo() -> None:
        init_runtime()
        await init_pg_pool()
        try:
            await create_product_service_view()
            logger.info("OK: views updated")
        finally:
            await close_pg_pool()

    asyncio.run(_demo())


if __name__ == "__main__":
    _run_cli()


# cd /home/copilot_superuser/petrunin/zena
# uv run python -m mcpserver.src.postgres.postgres_create_view
