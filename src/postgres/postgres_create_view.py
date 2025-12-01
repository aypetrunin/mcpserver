"""Модуль модуль создания вспомогательных view."""

import json
from typing import Dict

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from ..qdrant.retriever_common import POSTGRES_CONFIG  # type: ignore


def create_view_channel_services_keys() -> None:
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



if __name__ == "__main__":
    create_view_channel_services_keys()
    create_product_service_view()

# cd /home/copilot_superuser/petrunin/zena
# uv run python -m mcpserver.src.postgres.postgres_create_view