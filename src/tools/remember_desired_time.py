"""MCP-сервер фиксирующий выбранную клиентом времени записи."""

from typing import Any
from fastmcp import FastMCP

tool_desired_time = FastMCP(name="desired_time")


@tool_desired_time.tool(
    name="desired_time",
    description=(
        "Сохраняет выбранную клиентом время для записи.\n\n"
        "Args:\n"
        "- time_hhmm(str): желаемое время для записи в формате HH:MM (обязательно)\n"
        "Returns:\n"
        "- dict: {success: bool, office_id: str, office_address: str}"
    ),
)
async def remember_office_id(
    time_hhmm: str,
) -> dict[str, Any]:
    """Функция сохранения выбранного времени для записи на услугу."""

    return {"success": True, "desired_date": time_hhmm}
