"""MCP-сервер для поска расписания уроков клиента """

from typing import Any
from fastmcp import FastMCP

from ..crm.crm_get_client_lessons import go_get_client_lessons  # type: ignore

tool_get_client_lessons = FastMCP(name="get_client_lessons")

@tool_get_client_lessons.tool(
    name="get_client_lessons",
    description=(
        "Получение раписания руков.\n\n"
        "**Назначение:**\n"
        "Используется для получение расписания уроков для последующего переноса выбранного урока на другой день"
        "Используется при онлайн-бронировании.\n\n"
        "**Примеры запросов:**\n"
        '- "Нужно перенести урок"\n'
        '- "Ребенок заболел, не сможем прийти"\n'
        '- "Покажи расписание."\n\n'
        "**Args:**\n"
        "- phone(str): телефон клиента. **Обязательный параметр.**\n"
        "- channel_id (str): id учебной организации. **Обязательный параметр.**\n\n"
        "**Returns:**\n"
        "dict: Расписание уроков"
    ),
)
async def get_client_lessons_go(
    phone: str,
    channel_id: str,
) -> dict[str, Any]:
    """Функция получения расписания уроков.."""
    
    responce = await go_get_client_lessons(
        phone=phone,
        channel_id=channel_id
    )

    return responce
