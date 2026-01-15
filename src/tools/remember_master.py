"""MCP-сервер фиксирующий выбранную клиентом филиал."""

from typing import Any
from fastmcp import FastMCP

tool_remember_master = FastMCP(name="remember_master")


@tool_remember_master.tool(
    name="remember_master",
    description=(
        """Сохраняет выбранного клиентом мастера для записи.
        "Args:
        "- master_id (str): ID мастера(обязательно)
        "- master_name (str): Имя мастера (обязательно)
        "Returns:
        "- dict: {{success: bool, master_id: str, master_name: str}}

        Пример 1: Клиент: "Запиши меня к Ивановой"
            {{
                "master_id": "6326437",
                "master_name": "Иванова Валентина"
            }}
        Пример 2: Клиент: "Когда есть время у Марины"
            {{
                "master_id": "546758",
                "master_name": "Николаева Марина"
            }}
    """
    ),
)
async def remember_office(
    master_id: str,
    master_name: str,
) -> dict[str, Any]:
    """Функция сохранения сохранения выбранного клиентом мастера для записи."""

    return {"success": True, "master_id": master_id, "master_name": master_name}
