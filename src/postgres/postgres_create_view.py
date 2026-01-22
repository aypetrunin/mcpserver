"""
Модуль создания вспомогательных VIEW в Postgres (asyncpg + pool).

Зачем этот файл:
- В базе есть "представления" (VIEW) — это как виртуальные таблицы.
- Их нужно иногда создавать или обновлять (CREATE OR REPLACE VIEW).

Почему теперь asyncpg, а не psycopg2:
- psycopg2 — синхронный и блокирует event loop (плохо для async сервиса).
- asyncpg — асинхронный и хорошо работает в asyncio.
- pool позволяет не создавать новое соединение на каждый вызов.
"""

import os

from .db_pool import get_pg_pool, init_pg_pool, close_pg_pool
from src.runtime import init_runtime

# Таймаут на выполнение DDL (CREATE VIEW / DROP VIEW).
# DDL может быть чуть дольше обычных SELECT, поэтому по умолчанию 15 секунд.
PG_DDL_TIMEOUT_S = float(os.getenv("PG_DDL_TIMEOUT_S", "15"))


async def create_view_channel_services_keys() -> None:
    """
    Создаёт или заменяет представление view_channel_services_keys в базе.

    Что происходит:
    1) Берём соединение из пула
    2) Выполняем CREATE OR REPLACE VIEW
    3) Возвращаем соединение обратно в пул
    """
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        # conn.execute выполняет SQL, который не возвращает строки (DDL/UPDATE/INSERT).
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
    """
    Создаёт или заменяет представление product_service_view в базе.

    Тут важный момент:
    - у тебя раньше в psycopg2 было две команды подряд:
        DROP VIEW ...;
        CREATE VIEW ...;
    - Лучше выполнить их в транзакции:
      либо всё выполнится, либо ничего (если ошибка).

    В Postgres DDL тоже транзакционный (в большинстве случаев), поэтому так безопаснее.
    """
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        # Выполняем обе команды как один атомарный блок
        async with conn.transaction():
            await conn.execute(
                "DROP VIEW IF EXISTS product_service_view;",
                timeout=PG_DDL_TIMEOUT_S,
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
    """
    Удобная функция “сделай всё сразу”.

    Можно вызывать её:
    - при старте сервиса (если тебе надо гарантировать наличие VIEW)
    - или вручную отдельной командой в dev/maintenance
    """
    await create_view_channel_services_keys()
    await create_product_service_view()


if __name__ == "__main__":
    """
    Ручной запуск из консоли.

    Важно:
    - Здесь мы запускаем отдельный процесс, поэтому сами:
      1) загружаем env (init_runtime)
      2) создаём пул (init_pg_pool)
      3) вызываем нужную функцию
      4) закрываем пул (close_pg_pool)
    """

    import asyncio

    async def _demo() -> None:
        init_runtime()
        await init_pg_pool()
        try:
            # Выбирай что нужно:
            # await create_view_channel_services_keys()
            await create_product_service_view()
            # или:
            # await create_all_views()
            print("OK: views updated")
        finally:
            await close_pg_pool()

    asyncio.run(_demo())


# cd /home/copilot_superuser/petrunin/zena
# uv run python -m mcpserver.src.postgres.postgres_create_view