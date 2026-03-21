"""MCP-сервер для фиксации выбранной клиентом даты записи.

State-tool: сохраняет выбор пользователя в состоянии диалога.
"""

from __future__ import annotations

from datetime import datetime

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok


tool_remember_desired_date = FastMCP(name="remember_desired_date")


@tool_remember_desired_date.tool(
    name="remember_desired_date",
    description=(
        "Сохраняет выбранную клиентом дату для записи.\n\n"
        "**Args:**\n"
        "- date_iso (`str`, required): Желаемая дата записи в формате YYYY-MM-DD.\n\n"
        "**Returns:**\n"
        "- Payload[dict]\n\n"
        "**Примеры:**\n"
        '1) Клиент: "Запиши на Ленина на 10 января в 10"\n'
        '   Вход: {"date_iso": "2026-01-10"}\n\n'
        '2) Клиент: "на завтра"\n'
        '   Вход: {"date_iso": "2026-01-09"}\n'
    ),
)
async def remember_desired_date(date_iso: str) -> Payload[dict[str, str]]:
    """
    Описание результата.

    Контракт:
    - ok(data)  — дата валидна и зафиксирована
    - err(...)  — некорректный формат даты
    """
    # ------------------------------------------------------------
    # Валидация: дата обязательна
    # ------------------------------------------------------------
    if not isinstance(date_iso, str) or not date_iso.strip():
        return err(
            code="validation_error",
            error="Параметр date_iso обязателен и не должен быть пустым.",
        )

    # ------------------------------------------------------------
    # Валидация формата YYYY-MM-DD
    # ------------------------------------------------------------
    try:
        datetime.strptime(date_iso, "%Y-%m-%d")
    except ValueError:
        return err(
            code="validation_error",
            error="Некорректный формат даты. Ожидается YYYY-MM-DD.",
        )

    # ------------------------------------------------------------
    # Фиксация выбора (state)
    # ------------------------------------------------------------
    return ok({"desired_date": date_iso})
