"""MCP-сервер записи клиента на выбранную услугу на определенную дату и время."""

from typing import Any

from fastmcp import FastMCP

from ..crm.crm_record_time import record_time_async
from ..postgres.postgres_util import insert_dialog_state

tool_record_time = FastMCP(name="record_time")


@tool_record_time.tool(
    name="record_time",
    description=(
        """
        Запись клиента на медицинскую услугу в выбранную дату и время.

        **Назначение:**\n
        Используется, когда клиент подтвердил желание записаться на конкретную услугу в указанное время.
        Фиксирует запись с именем и телефоном клиента для последующего подтверждения или обработки администрацией.\n\n
        **Обязательные параметры:**\n
        - Все параметры обязательны для успешной записи.\n\n
        **Примеры запросов:**\n"
        - \"Запишите меня на массаж завтра в 11:00, меня зовут Анна, телефон 89991234567\"\n
        - \"Хочу записаться на УЗИ 22 июля в 15:00, Иван, 89161234567\"\n\n
        **Args:**\n
        - session_id(str): id dialog session. **Обязательный параметр.**\n
        - date (str): Дата записи в формате YYYY-MM-DD. Пример: '2025-07-22'. **Обязательный параметр.**\n
        - time (str): Время записи в формате HH:MM. Пример: '8:00', '13:00'. **Обязательный параметр.**\n
        - product_id (str): Идентификатор медицинской услуги. Обязательно две цифры разделенные дефисом. Пример формата: '1-232324'\n\n
        - client_id (int): ID клиента, записывающегося на услугу. Пример: 16677323 . **Обязательный параметр.**\n
        - master_id (int): ID мастера выполняющего услугу. Пример: 16677323 . **Не обязательный параметр.**\n
        **Returns:**\n
        - dict: success = True, если запись прошла успешно, иначе False.
        """
    ),
)
async def record_time(
    session_id: str,
    date: str,
    time: str,
    product_id: str,
    client_id: int,
    master_id: int = 0,
) -> dict[str, Any]:
    """Функция записи на выбранную услугу на определенную дату и время."""
    responce = await record_time_async(
        date=date,
        time=time,
        product_id=product_id,
        user_id=client_id,
        staff_id=master_id,
    )

    if responce:
        insert_dialog_state(
            session_id=session_id,
            record_time={
                "record_time": {
                    "date": date,
                    "time": time,
                    "product_id": product_id,
                    "client_id": client_id,
                    "master_id": master_id,
                }
            },
            status="postrecord",
        )

    return responce
