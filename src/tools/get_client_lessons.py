"""MCP-сервер для поиска расписания уроков клиента."""

from typing import Any

from fastmcp import FastMCP

from ..crm.crm_get_client_lessons import go_get_client_lessons  # type: ignore


tool_get_client_lessons = FastMCP(name="get_client_lessons")


@tool_get_client_lessons.tool(
    name="get_client_lessons",
    description=(
        "Получение расписания уроков.\n\n"
        "**Назначение:**\n"
        "Используется для получения расписания уроков клиента с целью "
        "последующего переноса выбранного урока на другой день. "
        "Также применяется при онлайн-бронировании.\n\n"
        "**Примеры запросов:**\n"
        '- "Нужно перенести урок"\n'
        '- "Ребёнок заболел, не сможем прийти"\n'
        '- "Покажи расписание"\n\n'
        "**Args:**\n"
        "- phone (`str`, required): Телефон клиента.\n"
        "- channel_id (`str`, required): ID учебной организации.\n\n"
        "**Returns:**\n"
        "- `dict`: Расписание уроков клиента.\n"
    ),
)
async def get_client_lessons_go(
    phone: str,
    channel_id: str,
) -> dict[str, Any]:
    """Получить расписание уроков клиента."""
    response = await go_get_client_lessons(
        phone=phone,
        channel_id=channel_id,
    )
    return response
