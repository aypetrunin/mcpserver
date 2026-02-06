"""MCP-сервер для фиксации выбранного клиентом мастера."""

from typing import Any

from fastmcp import FastMCP


tool_remember_master = FastMCP(name="remember_master")


@tool_remember_master.tool(
    name="remember_master",
    description=(
        "Сохраняет выбранного клиентом мастера для записи.\n\n"
        "**Args:**\n"
        "- master_id (`str`, required): ID мастера.\n"
        "- master_name (`str`, required): Имя мастера.\n\n"
        "**Returns:**\n"
        "- `dict`: {success: bool, master_id: str, master_name: str}\n\n"
        "**Примеры:**\n"
        '1) Клиент: "Запиши меня к Ивановой"\n'
        "   Вход:\n"
        '   {"master_id": "6326437", "master_name": "Иванова Валентина"}\n\n'
        '2) Клиент: "Когда есть время у Марины"\n'
        "   Вход:\n"
        '   {"master_id": "546758", "master_name": "Николаева Марина"}\n'
    ),
)
async def remember_master(
    master_id: str,
    master_name: str,
) -> dict[str, Any]:
    """Сохранить выбранного клиентом мастера для записи."""
    return {
        "success": True,
        "master_id": master_id,
        "master_name": master_name,
    }

