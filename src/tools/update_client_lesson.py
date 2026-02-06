"""MCP-сервер для переноса урока на другой день."""

from typing import Any

from fastmcp import FastMCP

from ..crm.crm_update_client_lesson import go_update_client_lesson  # type: ignore


tool_update_client_lesson = FastMCP(name="update_client_lesson")


@tool_update_client_lesson.tool(
    name="update_client_lesson",
    description=(
        "Перенос урока на другую дату и время.\n\n"
        "**Назначение:**\n"
        "Используется для переноса урока на другой день и время. "
        "Применяется при онлайн-бронировании.\n\n"
        "**Args:**\n"
        "- phone (`str`, required): Телефон клиента.\n"
        "- channel_id (`str`, required): ID учебной организации.\n"
        "- record_id (`str`, required): ID урока, который нужно перенести.\n"
        "- teacher (`str`, required): Имя преподавателя.\n"
        "- new_date (`str`, required): Новая дата урока (DD.MM.YYYY).\n"
        "- new_time (`str`, required): Новое время урока.\n"
        "- service (`str`, required): Название урока.\n"
        "- reason (`str`, required): Причина переноса урока.\n\n"
        "**Returns:**\n"
        "- `dict`: Результат переноса урока.\n"
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
    reason: str,
) -> dict[str, Any]:
    """Перенести урок на другую дату и время."""
    response = await go_update_client_lesson(
        phone=phone,
        channel_id=channel_id,
        record_id=record_id,
        instructor_name=teacher,
        new_date=new_date,
        new_time=new_time,
        service=service,
        reason=reason,
    )
    return response
