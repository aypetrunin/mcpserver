"""MCP-сервер для поиска свободных слотов по мастерам."""

from typing import Any
from fastmcp import FastMCP

from ..crm.crm_avaliable_time_for_master import avaliable_time_for_master_async  # type: ignore
from ..postgres.postgres_util import read_secondary_article_by_primary  # type: ignore
from ..postgres.postgres_util import insert_dialog_state  # type: ignore


tool_avaliable_time_for_master = FastMCP(name="avaliable_time_for_master")


@tool_avaliable_time_for_master.tool(
    name="avaliable_time_for_master",
    description=(
        "Получение списка доступного времени для записи на выбранную услугу в указанный день.\n\n"
        "**Назначение:**\n"
        "Используется для определения, на какое время клиент может записаться на услугу в выбранную дату.  "
        "Используется при онлайн-бронировании.\n\n"
        "**Примеры запросов:**\n"
        '- "Какие есть свободные слоты на УЗИ 5 августа?"\n'
        '- "Могу ли я записаться на приём к косметологу 12 июля?"\n'
        '- "Проверьте доступное время для гастроскопии на следующей неделе"\n\n'
        '- "Когда можно записаться к Кристине"\n\n'
        '- "Какие мастера могут выполнить услугу завтра."\n\n'
        "**Args:**\n"
        "- session_id(str): id dialog session. **Обязательный параметр.**\n"
        "- office_id(str): id филиала. **Обязательный параметр.**\n"
        "- product_id (str): Идентификатор медицинской услуги. Обязательно две цифры разделенные дефисом. Пример формата: '1-232324'. **Обязательный параметр.**\n\n"
        "- date (str): Дата на которую хочет записатьсяклиент в формате DD.MM.YYYY-MM-DD . Пример: '2025-07-22' **Обязательный параметр.**\n"
        "**Returns:**\n"
        "list[dict]: Список доступных слотов на услугу в формате DD.MM.YYYY-MM-DD  по мастерам [{'master_name': 'Кузнецова Кристина Александровна', 'master_id': 4216657, 'master_slots': ['2025-09-26 9:00', '2025-09-26 10:00', '2025-09-26 10:30']}]"
    ),
)
async def available_time_for_master(
    session_id: str,
    office_id: str,
    date: str,
    product_id: str,
) -> list[dict[str, Any]]:
    """Функция поска свободных слотов."""
    print("mcp_available_time_for_master")

    print(f"office_id: {office_id}")
    print(f"date: {date}")
    print(f"product_id: {product_id}")

    primary_channel = product_id.split('-')[0]
    print(f"primary_channel: {primary_channel}")

    if office_id != primary_channel:
        product_id = read_secondary_article_by_primary(
            primary_article=product_id,
            primary_channel=primary_channel,
            secondary_channel=office_id
        )

    print(f'avaliable_time_for_master_async (product_id: {product_id}, date: {date})')

    responce = await avaliable_time_for_master_async(date, product_id)

    insert_dialog_state(
        session_id=session_id,
        avaliable_time={"avaliable_time_for_master": responce},
    )

    return responce
