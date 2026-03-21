"""MCP-сервер, фиксирующий выбранный клиентом урок для переноса.

Назначение:
- сохранить выбранный урок и новые параметры (дата/время/причина)
- используется как state/memory tool
"""

from __future__ import annotations

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok


tool_remember_lesson_id = FastMCP(name="remember_lesson_id")


@tool_remember_lesson_id.tool(
    name="remember_lesson_id",
    description=(
        "Фиксация выбранного клиентом урока для переноса.\n\n"
        "**Пример:**\n"
        "«Перенесем урок с 15 января на 17 февраля»\n\n"
        "**Args:**\n"
        "- phone (`str`, required): телефон клиента\n"
        "- channel_id (`str`, required): id учебной организации\n"
        "- record_id (`str`, required): id урока для переноса\n"
        "- teacher (`str`, required): имя преподавателя\n"
        "- new_date (`str`, required): новая дата урока\n"
        "- new_time (`str`, required): новое время урока\n"
        "- service (`str`, required): название урока\n"
        "- reason (`str`, required): причина переноса\n\n"
        "**Returns:**\n"
        "- Payload[dict]\n"
    ),
)
async def remember_lesson_id(
    phone: str,
    channel_id: str,
    record_id: str,
    teacher: str,
    new_date: str,
    new_time: str,
    service: str,
    reason: str,
) -> Payload[dict[str, str]]:
    """
    Описание результата.

    Контракт:
    - ok(data)  — данные успешно зафиксированы
    - err(...)  — ошибка валидации входных параметров
    """
    # ------------------------------------------------------------
    # Валидация: все параметры обязательны
    # ------------------------------------------------------------
    required_fields = {
        "phone": phone,
        "channel_id": channel_id,
        "record_id": record_id,
        "teacher": teacher,
        "new_date": new_date,
        "new_time": new_time,
        "service": service,
        "reason": reason,
    }

    for name, value in required_fields.items():
        if not isinstance(value, str) or not value.strip():
            return err(
                code="validation_error",
                error=f"Параметр '{name}' обязателен и не должен быть пустым.",
            )

    # ------------------------------------------------------------
    # Фиксация состояния (ничего внешнего не вызываем)
    # ------------------------------------------------------------
    return ok(
        {
            "phone": phone,
            "channel_id": channel_id,
            "record_id": record_id,
            "teacher": teacher,
            "new_date": new_date,
            "new_time": new_time,
            "service": service,
            "reason": reason,
        }
    )
