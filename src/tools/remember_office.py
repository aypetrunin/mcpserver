"""MCP-сервер фиксирующий выбранную клиентом филиал."""

from typing import Any
from fastmcp import FastMCP

tool_remember_office = FastMCP(name="remember_office")


@tool_remember_office.tool(
    name="remember_office",
    description=(
        "Сохраняет выбранный клиентом филиал для записи.\n\n"
        "Args:\n"
        "- office_id (str): ID филиала (обязательно)\n"
        "- office_address (str): адрес филиала (обязательно)\n\n"
        "Returns:\n"
        "- dict: {success: bool, office_id: str, office_address: str}"
    ),
)
async def remember_office_id(
    office_id: str,
    office_address: str,
) -> dict[str, Any]:
    """Функция сохранения выбранной клиентом офиса для записи на услугу."""

    return {"success": True, "office_id": office_id, "office_address": office_address}
