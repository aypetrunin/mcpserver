"""MCP-сервер для поска расписания уроков клиента """

from typing import Any
from fastmcp import FastMCP

from ..crm.crm_get_client_statistics import go_get_client_statisics  # type: ignore

tool_get_client_statistics = FastMCP(name="get_client_statistics")

@tool_get_client_statistics.tool(
    name="get_client_statistics",
    description=(
        "Получение статистики посещений занятий клиентом.\n\n"
        "**Назначение:**\n"
        "Используется для получение статистики посещений клиентом занятий."
        "Используется при онлайн-бронировании.\n\n"
        "**Примеры запросов:**\n"
        '- "Какой у меня баланс?"\n'
        '- "Сколько занятий у меня осталось?"\n'
        '- "Покажи статистику."\n\n'
        '- "Покажи баланс."\n\n'
        "**Args:**\n"
        "- phone(str): телефон клиента. **Обязательный параметр.**\n"
        "- channel_id (str): id учебной организации. **Обязательный параметр.**\n\n"
        "**Returns:**\n"
        "dict: статстика/баланс посещений"
    ),
)
async def get_client_lessons_go(
    phone: str,
    channel_id: str,
) -> dict[str, Any]:
    """Функция получения расписания уроков.."""
    
    responce = await go_get_client_statisics(
        phone=phone,
        channel_id=channel_id
    )

    return responce
