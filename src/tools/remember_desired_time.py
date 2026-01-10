"""MCP-сервер фиксирующий выбранную клиентом времени записи."""

from typing import Any
from fastmcp import FastMCP

tool_remember_desired_time = FastMCP(name="remember_desired_time")


@tool_remember_desired_time.tool(
    name="remember_desired_time",
    description=(
        """Сохраняет выбранную клиентом время для записи.
        Args:\n"
        - time_hhmm(str): желаемое время для записи в формате HH:MM (обязательно)
        Returns:
        - dict: {{success: bool, office_id: str, office_address: str}}

        Пример 1: Клиент: "Запиши на Ленина на завтра в 10"
            Вход: desired_time = 
            {{
                "time_hhmm": "10:00",
            }}
        Пример 2: Клиент: "на 12:00"
            Вход: desired_time = 
            {{
                "time_hhmm": "12:00",
            }}
        """
    ),
)
async def remember_desired_time(
    time_hhmm: str,
) -> dict[str, Any]:
    """Функция сохранения выбранного времени для записи на услугу."""

    return {"success": True, "desired_time": time_hhmm}
