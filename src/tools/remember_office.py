"""MCP-сервер фиксирующий выбранную клиентом филиал."""

from typing import Any
from fastmcp import FastMCP

tool_remember_office = FastMCP(name="remember_office")


@tool_remember_office.tool(
    name="remember_office",
    description=(
        """Сохраняет выбранный клиентом филиал для записи.
        "Args:
        "- office_id (str): ID филиала (обязательно)
        "- office_address (str): адрес филиала (обязательно)
        "Returns:
        "- dict: {{success: bool, office_id: str, office_address: str}}

        Пример 1: Клиент: "Запиши на Ленина на завтра в 10"
            Вход: desired_time = 
            {{
                "office_id": "192",
                "office_address": "пр. Леннина, 2"
            }}
        Пример 2: Клиент: "хочу на мира"
            Вход: desired_time = 
            {{
                "office_id": "10",
                "office_address": "ул. Мира, 21"
            }}
    """
    ),
)
async def remember_office(
    office_id: str,
    office_address: str,
) -> dict[str, Any]:
    """Функция сохранения выбранной клиентом офиса для записи на услугу."""

    return {"success": True, "office_id": office_id, "office_address": office_address}
