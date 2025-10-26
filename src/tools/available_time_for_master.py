from fastmcp import FastMCP

from ..postgres.postgres_util import insert_dialog_state
from ..crm.avaliable_time_for_master import avaliable_time_for_master_async

tool_available_time_for_master = FastMCP(name="available_time_for_master")

@tool_available_time_for_master.tool(
    name="available_time_for_master",
    description=(
        "Получение списка доступного времени для записи на выбранную услугу в указанный день.\n\n"
        "**Назначение:**\n"
        "Используется для определения, на какое время клиент может записаться на услугу в выбранную дату.  "
        "Используется при онлайн-бронировании.\n\n"
        "**Примеры запросов:**\n"
        "- \"Какие есть свободные слоты на УЗИ 5 августа?\"\n"
        "- \"Могу ли я записаться на приём к косметологу 12 июля?\"\n"
        "- \"Проверьте доступное время для гастроскопии на следующей неделе\"\n\n"
        "- \"Когда можно записаться к Кристине\"\n\n"
        "- \"Какие мастера могут выполнить услугу завтра.\"\n\n"
        "**Args:**\n"
        "- session_id(str): id dialog session. **Обязательный параметр.**\n"
        "- product_id (str): Идентификатор медицинской услуги. Обязательно две цифры разделенные дефисом. Пример формата: '1-232324'. **Обязательный параметр.**\n\n"
        "- date (str): Дата на которую хочет записатьсяклиент в формате DD.MM.YYYY-MM-DD . Пример: '2025-07-22' **Обязательный параметр.**\n"
        "**Returns:**\n"
        "list[dict]: Список доступных слотов на услугу в формате DD.MM.YYYY-MM-DD  по мастерам [{'master_name': 'Кузнецова Кристина Александровна', 'master_id': 4216657, 'master_slots': ['2025-09-26 9:00', '2025-09-26 10:00', '2025-09-26 10:30']}]"
    )
)
async def available_time_for_master(session_id: str, date: str, product_id: str) -> list[dict]:
    print('mcp_available_time_for_master')

    responce = await avaliable_time_for_master_async(date, product_id)
    print(responce)

    insert_dialog_state(
        session_id=session_id,
        avaliable_time={"avaliable_time_for_master": responce},
    )

    return responce
