"""MCP-сервер для переноса урока на другой день"""

from typing import Any
from fastmcp import FastMCP

from ..crm.crm_update_client_lesson import go_update_client_lesson  # type: ignore

tool_update_client_lesson = FastMCP(name="update_client_lesson")

@tool_update_client_lesson.tool(
    name="update_client_lesson",
    description=(
        "Перенос урока на другую дату и время\n\n"
        "**Назначение:**\n"
        "Используется для переноса урока на другой день и время"
        "Используется при онлайн-бронировании.\n\n"
        "**Args:**\n"
        "- phone(str): телефон клиента. **Обязательный параметр.**\n"
        "- channel_id (str): id учебной организации. **Обязательный параметр.**\n\n"
        "- record_id (str): id урока который нужно перенести. **Обязательный параметр.**\n\n"
        "- teacher (str): имя учителя урока который нужно перенести.**Обязательный параметр.**\n\n"
        "- new_date (str): новая дата урока в формате DD.MM.YYYY **Обязательный параметр.**\n\n"
        "- new_time (str): новое время урока. **Обязательный параметр.**\n\n"
        "- service (str): название урока **Обязательный параметр.**\n\n"
        "- reason (str): причина переноса урока **Обязательный параметр**\n\n"
        "**Returns:**\n"
        "dict: результат переноса"
    ),
)
async def update_client_lesson_go(
    phone: str,
    channel_id: str,
    record_id: str,
    teacher: str,
    new_date: str,
    new_time: str,
    service: str,
    reason: str
) -> dict[str, Any]:
    """Функция переноса урока."""
    
    responce = await go_update_client_lesson(
        phone=phone,
        channel_id=channel_id,
        record_id = record_id,
        instructor_name = teacher,
        new_date = new_date,
        new_time = new_time,
        service = service,
        reason = reason,
    )

    return responce


