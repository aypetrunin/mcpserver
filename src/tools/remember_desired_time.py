"""MCP-сервер для фиксации выбранного клиентом времени записи.

State-tool: сохраняет выбор пользователя в состоянии диалога.
"""

from __future__ import annotations

from datetime import datetime

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok


tool_remember_desired_time = FastMCP(name="remember_desired_time")


@tool_remember_desired_time.tool(
    name="remember_desired_time",
    description=(
        "Сохраняет выбранное клиентом время для записи.\n\n"
        "**Args:**\n"
        "- time_hhmm (`str`, required): Желаемое время записи в формате HH:MM.\n\n"
        "**Returns:**\n"
        "- Payload[dict]\n\n"
        "**Примеры:**\n"
        '1) Клиент: "Запиши на Ленина на завтра в 10"\n'
        '   Вход: {"time_hhmm": "10:00"}\n\n'
        '2) Клиент: "на 12:00"\n'
        '   Вход: {"time_hhmm": "12:00"}\n'
    ),
)
async def remember_desired_time(time_hhmm: str) -> Payload[dict[str, str]]:
    """
    Описание результата.

    Контракт:
    - ok(data)  — время валидно и зафиксировано
    - err(...)  — некорректный формат времени
    """
    # ------------------------------------------------------------
    # Валидация: параметр обязателен
    # ------------------------------------------------------------
    if not isinstance(time_hhmm, str) or not time_hhmm.strip():
        return err(
            code="validation_error",
            error="Параметр time_hhmm обязателен и не должен быть пустым.",
        )

    # ------------------------------------------------------------
    # Валидация формата HH:MM
    # ------------------------------------------------------------
    try:
        datetime.strptime(time_hhmm, "%H:%M")
    except ValueError:
        return err(
            code="validation_error",
            error="Некорректный формат времени. Ожидается HH:MM.",
        )

    # ------------------------------------------------------------
    # Фиксация выбора (state)
    # ------------------------------------------------------------
    return ok({"desired_time": time_hhmm})
