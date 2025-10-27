"""Модуль вспомогательной утилиты записи информации в dialog_state.

Запись производится mcp-серверами для фиксации свое работы.
Изменения статума диалога, выбранной услуги, свободных слотов, результатов поиска услуг.
"""

import json
from typing import Dict

import psycopg2
from dotenv import load_dotenv

from ..qdrant.retriever_common import POSTGRES_CONFIG

load_dotenv()

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
    # conn = psycopg2.connect(
    #     user=os.getenv("POSTGRES_USER"),
    #     password=os.getenv("POSTGRES_PASSWORD"),
    #     dbname=os.getenv("POSTGRES_DB"),
    #     host=os.getenv("POSTGRES_HOST"),
    #     port=os.getenv("POSTGRES_PORT"),
    # )
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


# def update_agent_chat_history(
#     session_id: str,
#     product_id: dict | None = None,
#     product_search: dict | None = None,
#     product_type: dict | None = None,
#     body_parts: dict | None = None,
#     record_time: dict | None = None,
#     avaliable_time: dict | None = None,
#     status: str | None = None,
# ) -> None:
#     # conn = psycopg2.connect(
#     #     user=os.getenv("POSTGRES_USER"),
#     #     password=os.getenv("POSTGRES_PASSWORD"),
#     #     dbname=os.getenv("POSTGRES_DB"),
#     #     host=os.getenv("POSTGRES_HOST"),
#     #     port=os.getenv("POSTGRES_PORT"),
#     # )
#     conn = psycopg2.connect(**POSTGRES_CONFIG)
#     try:
#         with conn.cursor() as cur:
#             # Находим запись с максимальным id по session_id
#             cur.execute(
#                 """
#                 SELECT id FROM agent_chat_histories
#                 WHERE session_id = %s
#                 ORDER BY id DESC
#                 LIMIT 1
#             """,
#                 (session_id,),
#             )
#             row = cur.fetchone()
#             if row is None:
#                 print(f"Нет записей с session_id = {session_id}")
#                 return

#             record_id = row[0]

#             # Формируем список полей для обновления
#             fields = []
#             values = []

#             if product_id is not None:
#                 fields.append("product_id = %s")
#                 values.append(json.dumps(product_id))
#             if product_search is not None:
#                 fields.append("product_search = %s")
#                 values.append(json.dumps(product_search))
#             if product_type is not None:
#                 fields.append("product_type = %s")
#                 values.append(json.dumps(product_type))
#             if body_parts is not None:
#                 fields.append("body_parts = %s")
#                 values.append(json.dumps(body_parts))
#             if record_time is not None:
#                 fields.append("record_time = %s")
#                 values.append(json.dumps(record_time))
#             if avaliable_time is not None:
#                 fields.append("avaliable_time = %s")
#                 values.append(json.dumps(avaliable_time))
#             if status:
#                 fields.append("status = %s")
#                 values.append(status)

#             if not fields:
#                 print("Нет данных для обновления.")
#                 return

#             values.append(record_id)
#             query = f"""
#                 UPDATE agent_chat_histories
#                 SET {", ".join(fields)}
#                 WHERE id = %s
#             """

#             cur.execute(query, values)
#             conn.commit()
#             print(f"Статус: {status}")
#     finally:
#         conn.close()