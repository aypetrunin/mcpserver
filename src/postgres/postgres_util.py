"""Модуль вспомогательной утилиты записи информации в dialog_state.

Запись производится mcp-серверами для фиксации свое работы.
Изменения статума диалога, выбранной услуги, свободных слотов, результатов поиска услуг.
"""

import json
from typing import Dict, Any

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from ..qdrant.retriever_common import POSTGRES_CONFIG  # type: ignore


def insert_dialog_state(
    session_id: str,
    name: str | None = None,
    product_id: dict[str, Any] | None = None,
    product_search: dict[str, Any] | None = None,
    product_type: dict[str, Any] | None = None,
    body_parts: dict[str, Any] | None = None,
    record_time: dict[str, Any] | None = None,
    avaliable_time: dict[str, Any] | None = None,
    recommendations: dict[str, Any] | None = None,
) -> int | None:
    """Функция записи в таблицу dialog_state вспомогательной информации."""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    try:
        # print("insert_dialog_state")
        with conn.cursor() as cur:
            # --- динамическое формирование data ---
            data = {}
            if product_id is not None:
                data["product_id"] = product_id
            if product_search is not None:
                data["product_search"] = product_search
            if product_type is not None:
                data["product_type"] = product_type
            if body_parts is not None:
                data["body_parts"] = body_parts
            if record_time is not None:
                data["record_time"] = record_time
            if avaliable_time is not None:
                data["avaliable_time"] = avaliable_time
            if recommendations is not None:
                data["recommendations"] = recommendations

            if not data:
                # print("Нет данных для вставки.")
                return None

            # --- вставка записи ---
            cur.execute(
                """
                INSERT INTO dialog_state (session_id, name, data)
                VALUES (%s, %s, %s)
                RETURNING id
            """,
                (
                    session_id,
                    name,
                    json.dumps(data),  # динамически собранный JSON
                ),
            )

            new_id = cur.fetchone()[0]
            conn.commit()
            # print(f"Создана запись dialog_state id={new_id}")
            return new_id
    finally:
        conn.close()


def select_key(channel_id: int) -> dict[str, Any]:
    """Функция выбора уникальных ключей из view для данного канала."""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT body_parts, indications_key, contraindications_key
                FROM view_channel_services_keys
                WHERE channel_id = %s;
            """
            cur.execute(sql, (channel_id,))
            data = cur.fetchone()
            if data is not None:
                return {
                    "body_parts": data[0],
                    "indications_key": data[1],
                    "contraindications_key": data[2],
                }
            else:
                return {}
    finally:
        conn.close()


def create_or_replace_view() -> None:
    """Функция создания или замены представления view_channel_services_keys в базе."""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # для выполнения CREATE VIEW без транзакции
    try:
        with conn.cursor() as cur:
            sql = """
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
            """
            cur.execute(sql)
    finally:
        conn.close()


def create_product_service_view() -> None:
    """Функция создания или замены представления product_service_view в базе."""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # Для выполнения DDL вне транзакций
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DROP VIEW IF EXISTS product_service_view;
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
            """)
    finally:
        conn.close()


def read_secondary_article_by_primary(
    primary_article: str,
    primary_channel: int,
    secondary_channel: int,
) -> str | None:
    """
    Возвращает article связанного (secondary) товара
    для primary_article.
    Если связанного товара нет — возвращает None.
    """
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    p_secondary.article
                FROM products p_primary
                LEFT JOIN products p_secondary
                  ON p_primary.product_name = p_secondary.product_name
                 AND p_secondary.channel_id = %s
                WHERE p_primary.channel_id = %s
                  AND p_primary.article = %s
                LIMIT 1;
                """,
                (
                    secondary_channel,
                    primary_channel,
                    primary_article,
                ),
            )

            row = cur.fetchone()
            if row is None:
                return None

            return row[0]
    finally:
        conn.close()


def get_product_name_for_id(product_id: str) -> str | None:
    """Функция возвращает название услуги по его id."""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.product_name
                FROM products p
                WHERE p.article = %s
                """,
                (product_id,)
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()



if __name__ == "__main__":
    result = select_key(channel_id=1)
    # print(f"\n{result}")

# cd /home/copilot_superuser/petrunin/zena
# uv run python -m mcpserver.src.postgres.postgres_util