"""MCP-сервер для фиксации выбранной клиентом даты записи."""

from typing import Any

from fastmcp import FastMCP


tool_remember_desired_date = FastMCP(name="remember_desired_date")


@tool_remember_desired_date.tool(
    name="remember_desired_date",
    description=(
        "Сохраняет выбранную клиентом дату для записи.\n\n"
        "**Args:**\n"
        "- date_iso (`str`, required): Желаемая дата записи в формате YYYY-MM-DD.\n\n"
        "**Returns:**\n"
        "- `dict`: {success: bool, desired_date: str}\n\n"
        "**Примеры:**\n"
        '1) Клиент: "Запиши на Ленина на 10 января в 10"\n'
        "   Вход:\n"
        '   {"date_iso": "2026-01-10"}\n\n'
        '2) Клиент: "на завтра"\n'
        "   Вход:\n"
        '   {"date_iso": "2026-01-09"}\n'
    ),
)
async def remember_desired_date(date_iso: str) -> dict[str, Any]:
    """Сохранить выбранную клиентом дату записи."""
    return {"success": True, "desired_date": date_iso}

