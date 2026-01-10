"""MCP-сервер фиксирующий выбранную клиентом дату записи."""

from typing import Any
from fastmcp import FastMCP

tool_remember_desired_date = FastMCP(name="remember_desired_date")


@tool_remember_desired_date.tool(
    name="remember_desired_date",
    description=(
        """Сохраняет выбранную клиентом дату для записи.
        Args:\n"
        - date_iso(str): желаемая дата записи в формате YYYY-MM-DD (обязательно)
        Returns:
        - dict: {{success: bool, office_id: str, office_address: str}}

        Пример 1: Клиент: "Запиши на Ленина на 10 января в 10"
            Вход: desired_date = 
            {{
                "date_iso": "2026-01-10",
            }}
        Пример 2: Клиент: "на завтра"
            Вход: desired_date = 
            {{
                "date_iso": "2026-01-09",
            }}
        """
    ),
)
async def remember_desired_date(
    date_iso: str,
) -> dict[str, Any]:
    """Функция сохранения выбранной даты записи на услугу."""

    return {"success": True, "desired_date": date_iso}
