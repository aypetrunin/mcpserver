"""MCP-сервер для фиксации выбранного клиентом времени записи."""

from typing import Any

from fastmcp import FastMCP


tool_remember_desired_time = FastMCP(name="remember_desired_time")


@tool_remember_desired_time.tool(
    name="remember_desired_time",
    description=(
        "Сохраняет выбранное клиентом время для записи.\n\n"
        "**Args:**\n"
        "- time_hhmm (`str`, required): Желаемое время записи в формате HH:MM.\n\n"
        "**Returns:**\n"
        "- `dict`: {success: bool, desired_time: str}\n\n"
        "**Примеры:**\n"
        '1) Клиент: "Запиши на Ленина на завтра в 10"\n'
        "   Вход:\n"
        '   {"time_hhmm": "10:00"}\n\n'
        '2) Клиент: "на 12:00"\n'
        "   Вход:\n"
        '   {"time_hhmm": "12:00"}\n'
    ),
)
async def remember_desired_time(time_hhmm: str) -> dict[str, Any]:
    """Сохранить выбранное клиентом время записи."""
    return {"success": True, "desired_time": time_hhmm}
