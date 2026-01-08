"""MCP-сервер фиксирующий выбранную клиентом дату записи."""

from typing import Any
from fastmcp import FastMCP

tool_desired_date = FastMCP(name="desired_date")


@tool_desired_date.tool(
    name="desired_date",
    description=(
        "Сохраняет выбранную клиентом дату для записи.\n\n"
        "Args:\n"
        "- date_iso(str): желаемая дата записи в формате YYYY-MM-DD (обязательно)\n"
        "Returns:\n"
        "- dict: {success: bool, office_id: str, office_address: str}"
    ),
)
async def remember_office_id(
    date_iso: str,
) -> dict[str, Any]:
    """Функция сохранения выбранной даты записи на услугу."""

    return {"success": True, "desired_date": date_iso}
