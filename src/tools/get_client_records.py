"""MCP-сервер для поиска текущих записей услуг клиента"""

from typing import Any, Dict
from fastmcp import FastMCP

from ..crm.crm_get_client_records import get_client_records  # type: ignore

tool_records = FastMCP(name="records")


@tool_records.tool(
    name="records",
    description=(
        "Возвращает список услуг, на которые записан клиент.\n\n"
        "**Назначение:**\n"
        "Используется, когда клиент интересуется своими записями, "
        "чтобы увидеть расписание, перенести или отменить визит.\n\n"
        "**Примеры вопросов:**\n"
        "- Когда я записан?\n"
        "- На какое время я записан?\n"
        "- К кому я записан?\n"
        "- В каком офисе у меня запись?\n\n"
        "**Args:**\n"
        "- `user_companychat` (`str`, required): ID пользователя.\n"
        "- `channel_id` (`str`, required): ID канала.\n\n"
        "**Returns:**\n"
        "- `dict`\n"
    ),
)
async def records(
    user_companychat: str,
    channel_id: str,
) -> Dict[str, Any]:
    """Функция поиска текущих записей на услуги."""
    try:
        return await get_client_records(
            user_companychat=int(user_companychat),
            channel_id=int(channel_id),
        )
    except ValueError:
        return {
            "success": False,
            "data": [],
            "error": "Некорректный идентификатор пользователя",
        }
