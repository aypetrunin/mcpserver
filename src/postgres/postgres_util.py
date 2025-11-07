"""Модуль вспомогательной утилиты записи информации в dialog_state.

Запись производится mcp-серверами для фиксации свое работы.
Изменения статума диалога, выбранной услуги, свободных слотов, результатов поиска услуг.
"""

import json
from typing import Dict

import psycopg2

from ..qdrant.retriever_common import POSTGRES_CONFIG


def insert_dialog_state(
    session_id: str,
    name: str | None = None,
    product_id: Dict | None = None,
    product_search: Dict | None = None,
    product_type: Dict | None = None,
    body_parts: Dict | None = None,
    record_time: Dict | None = None,
    avaliable_time: Dict | None = None,
    status: str | None = None,
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
            if status is not None:
                data["status"] = status

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


def select_indications_key(channel_id: int) -> str | None:
    """Функция выбора уникальных показаний."""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT string_agg('"' || unique_key || '"', ' ') AS all_keys
                FROM (
                    SELECT DISTINCT TRIM(key) AS unique_key
                    FROM (
                        SELECT regexp_split_to_table(indications_key, '[,]+') AS key
                        FROM services
                        WHERE indications_key IS NOT NULL
                          AND channel_id = %s
                    ) sub
                    WHERE key <> ''
                ) uniq_keys;
                """,
                (channel_id,),
            )
            indications_key = cur.fetchone()[0]
            return indications_key
    finally:
        conn.close()


def select_key_(channel_id: int, key: str) -> str | None:
    """Функция выбора уникальных ключей из выбранного столбца."""
    assert key in {
        "body_parts",
        "indications_key",
        "contraindications_key",
    }  # допустимые столбцы
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    try:
        with conn.cursor() as cur:
            sql = f"""
                SELECT string_agg('"' || unique_key || '"', ', ') AS all_keys
                FROM (
                    SELECT DISTINCT TRIM(k) AS unique_key
                    FROM (
                        SELECT regexp_split_to_table({key}, '[,\n]+') AS k
                        FROM services
                        WHERE {key} IS NOT NULL
                          AND channel_id = %s
                    ) sub
                    WHERE k <> ''
                ) uniq_keys;
            """
            cur.execute(sql, (channel_id,))
            all_keys = cur.fetchone()[0]
            return all_keys
    finally:
        conn.close()


def select_key(channel_id: int) -> str | None:
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
                return None  # либо '', если нужен пустой результат
    finally:
        conn.close()


if __name__ == "__main__":
    result = select_key(channel_id=1)
    # print(f"\n{result}")

# cd /home/copilot_superuser/petrunin/zena
# uv run python -m mcpserver.src.postgres.postgres_util
