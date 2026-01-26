"""MCP-сервер для поиска текущих записей услуг клиента"""

from typing import Any, Dict
from fastmcp import FastMCP

from ..crm.crm_delete_client_record import delete_client_record  # type: ignore

tool_record_delete = FastMCP(name="record_delete")


@tool_record_delete.tool(
    name="record_delete",
    description=(
        "Удаление записи на услугу в CRM.\n\n"
        "**Назначение:**\n"
        "Используется, когда клиент отменить свою запись на услугу.\n\n"
        "чтобы увидеть расписание, перенести или отменить визит.\n\n"
        "**Примеры вопросов:**\n"
        "- Отмени запись на сфера-массаж на понедельник.\n"
        "**Args:**\n"
        "- `user_companychat` (`str`, required): ID пользователя.\n"
        "- `channel_id` (`str`, required): ID канала.\n\n"
        "- `record_id` (`str`, required): ID записи в CRM.\n\n"
        "**Returns:**\n"
        "- `dict`\n"
    ),
)
async def records(
    user_companychat: str,
    channel_id: str,
    record_id: str,
) -> Dict[str, Any]:
    """Функция удаления услуги."""
    try:
        return await delete_client_record(
            user_companychat=int(user_companychat),
            channel_id=int(channel_id),
            record_id=int(record_id),
        )
    except ValueError:
        return {
            "success": False,
            "error": "Записи не существует.",
        }
