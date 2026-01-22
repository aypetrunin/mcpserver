"""
postgres_util.py (asyncpg + pool)

Модуль вспомогательных утилит работы с Postgres.

Раньше здесь был psycopg2:
- на каждый вызов создавалось новое соединение
- это блокировало event loop в async-сервисе
- и было медленнее/тяжелее

Теперь:
- используется asyncpg pool (создаётся 1 раз на старте процесса)
- каждое обращение к БД берёт соединение из пула на время операции
- у запросов есть таймауты (чтобы не зависать навсегда)
"""

import os
from typing import Any

from asyncpg import Record

from .db_pool import get_pg_pool

# Таймаут на один SQL-запрос (клиентский).
# Серверный таймаут (statement_timeout) задаётся при init пула.
PG_QUERY_TIMEOUT_S = float(os.getenv("PG_QUERY_TIMEOUT_S", "5"))


async def select_key(channel_id: int) -> dict[str, Any]:
    """
    Выбирает уникальные ключи из view для данного канала.

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
    """
    Создаёт или заменяет VIEW view_channel_services_keys.

    В psycopg2 ты ставил AUTOCOMMIT "для DDL".
    В asyncpg это не нужно так делать вручную:
    - execute выполняется как отдельная команда
    - плюс у нас есть statement_timeout на уровне соединения

    Важно:
    - команда может занимать время (зависит от объёма таблиц)
    - поэтому нужен таймаут (и серверный, и клиентский)
    """
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
                            FROM services s
                            WHERE s.channel_id = ch.id AND s.body_parts IS NOT NULL
                        ) AS sub
                        WHERE b <> ''
                    ) uniq
                ) AS body_parts,
                (
                    SELECT string_agg('"' || ik || '"', ', ')
                    FROM (
                        SELECT DISTINCT TRIM(i) AS ik
                        FROM (
                            SELECT regexp_split_to_table(s.indications_key, '[,]+') AS i
                            FROM services s
                            WHERE s.channel_id = ch.id AND s.indications_key IS NOT NULL
                        ) AS sub
                        WHERE i <> ''
                    ) uniq
                ) AS indications_key,
                (
                    SELECT string_agg('"' || ck || '"', ', ')
                    FROM (
                        SELECT DISTINCT TRIM(c) AS ck
                        FROM (
                            SELECT regexp_split_to_table(s.contraindications_key, '[,]+') AS c
                            FROM services s
                            WHERE s.channel_id = ch.id AND s.contraindications_key IS NOT NULL
                        ) AS sub
                        WHERE c <> ''
                    ) uniq
                ) AS contraindications_key
            FROM channel ch
            WHERE ch.url_googlesheet_data IS NOT NULL AND TRIM(ch.url_googlesheet_data) <> ''
            ORDER BY ch.id;
            """,
            timeout=PG_QUERY_TIMEOUT_S,
        )


async def create_product_service_view() -> None:
    """
    Создаёт или заменяет VIEW product_service_view.

    Важно:
    - тут две команды (DROP + CREATE)
    - чтобы было атомарнее, можно завернуть в транзакцию
    - но для VIEW это обычно не критично; всё равно делаем транзакцию "для порядка"
    """
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DROP VIEW IF EXISTS product_service_view;",
                timeout=PG_QUERY_TIMEOUT_S,
            )

            await conn.execute(
                """
                CREATE VIEW product_service_view AS
                SELECT
                    p.channel_id,
                    p.product_id as id,
                    p.article AS product_id,
                    p.product_full_name AS product_name,
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
                timeout=PG_QUERY_TIMEOUT_S,
            )


async def read_secondary_article_by_primary(
    primary_article: str,
    primary_channel: int,
    secondary_channel: int,
) -> str | None:
    """
    Возвращает article связанного (secondary) товара для primary_article.
    Если связанного товара нет — возвращает None.
    """
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        value: str | None = await conn.fetchval(
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
        return value


async def get_product_name_for_id(product_id: str) -> str | None:
    """
    Возвращает название продукта по его article/id.
    Если продукта нет — None.
    """
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        value: str | None = await conn.fetchval(
            """
            SELECT p.product_name
            FROM products p
            WHERE p.article = $1
            """,
            product_id,
            timeout=PG_QUERY_TIMEOUT_S,
        )
        return value


# ------------------------------------------------------------------------------
# ЛОКАЛЬНЫЙ ЗАПУСК (для ручной проверки)
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    """
    ВАЖНО:
    - теперь функции асинхронные
    - для запуска нужно:
        1) инициализировать пул
        2) вызвать нужную функцию
        3) закрыть пул

    Пример:
    uv run python -m mcpserver.src.postgres.postgres_util
    """

    import asyncio
    from ..runtime import init_runtime
    from .db_pool import init_pg_pool, close_pg_pool

    init_runtime()  # ← ВАЖНО

    async def _demo() -> None:
        await init_pg_pool()
        try:
            result = await select_key(channel_id=1)
            print(result)
        finally:
            await close_pg_pool()

    asyncio.run(_demo())


# cd /home/copilot_superuser/petrunin/zena
# uv run python -m mcpserver.src.postgres.postgres_util
