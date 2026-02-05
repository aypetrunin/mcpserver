"""MCP-сервер для поиска свободных слотов по мастерам."""

import logging

from fastmcp import FastMCP
from typing import TypedDict

from ..crm.crm_avaliable_time_for_master_list import avaliable_time_for_master_list_async  # type: ignore

logger = logging.getLogger(__name__)

class AvailableTimePayload(TypedDict):
    date: str
    service_id: str
    service_name: str

tool_avaliable_time_for_master_list = FastMCP(name="avaliable_time_for_master_list")

@tool_avaliable_time_for_master_list.tool(
    name="avaliable_time_for_master_list",
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
        '- "На завтра что у Вас есть?"\n\n'
        '- "На 1 декабря ...?"\n\n'
        '- "На вечер есть?"\n\n'
        '- "К косметологу можно?"\n\n'
        '- "Свободно завтра?"\n\n'
        '- "На ближайшее время?"\n\n'
        '- "На пятницу утром?"\n\n'
        '- "В субботу кто работает?"\n\n'
        '- "К Кристине запись?"\n\n'
        '- "На ближайшие выходные?"\n\n'
        '- "После обеда свободно?"\n\n'
        '- "На завтра услуги?"\n\n'
        '- "До 18:00 нельзя?"\n\n'
        '- "На 12 число часы?"\n\n'
        '- "В среду?"\n\n'
        '- "На следующей неделе?"\n\n'

        "**Args:**\n"
        "- product_id (list[str}): Список идентификаторов медицинских услуг. Обязательно две цифры разделенные дефисом. Пример формата: ['1-232324', '1-237654']. **Обязательный параметр.**\n\n"
        "- product_name(list[str}): Список названий медицинских услуг. **Обязательный параметр.**\n\n"
        "- date (str): Дата на которую хочет записатьсяклиент в формате DD.MM.YYYY-MM-DD . Пример: '2025-07-22' **Обязательный параметр.**\n"
        "**Returns:**\n"
        "tuple[list[dict], list[dict]]: Список доступных слотов на услугу в формате DD.MM.YYYY-MM-DD  по мастерам [{'master_name': 'Кузнецова Кристина Александровна', 'master_id': 4216657, 'master_slots': ['2025-09-26 9:00', '2025-09-26 10:00', '2025-09-26 10:30']}], []"
    ),
)
async def avaliable_time_for_master(
    date: str,
    product_id: list[str],
    product_name: list[str]
) -> tuple[list[dict], list[dict]]:
    """Функция поиска свободных слотов."""

    list_products_id = ', '.join(product_id)
    list_products_name = ', '.join(product_name)

    payload: AvailableTimePayload = {
        "date": date,
        "service_id": list_products_id,
        "service_name": list_products_name,
    }

    sequences, avaliable_sequences = await avaliable_time_for_master_list_async(**payload)

    logger.info("Вход: payload=%s", payload)
    logger.info("Выход: sequences=%s", sequences)
    logger.info("Выход: avaliable_sequences=%s", avaliable_sequences)

    return sequences, avaliable_sequences