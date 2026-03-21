"""MCP-сервер для фиксации выбранного клиентом филиала.

State-tool: сохраняет выбор пользователя в состоянии диалога.
"""

from __future__ import annotations

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok


tool_remember_office = FastMCP(name="remember_office")


@tool_remember_office.tool(
    name="remember_office",
    description=(
        "Сохраняет выбранный клиентом филиал для записи.\n\n"
        "**Args:**\n"
        "- office_id (`str`, required): ID филиала.\n"
        "- office_address (`str`, required): Адрес филиала.\n\n"
        "**Returns:**\n"
        "- Payload[dict]\n\n"
        "**Примеры:**\n"
        '1) Клиент: "Запиши на Ленина на завтра в 10"\n'
        '   Вход: {"office_id": "192", "office_address": "пр. Ленина, 2"}\n\n'
        '2) Клиент: "Хочу на Мира"\n'
        '   Вход: {"office_id": "10", "office_address": "ул. Мира, 21"}\n'
    ),
)
async def remember_office(
    office_id: str,
    office_address: str,
) -> Payload[dict[str, str]]:
    """
    Описание результата.

    Контракт:
    - ok(data)  — филиал валиден и зафиксирован
    - err(...)  — ошибка валидации
    """
    # ------------------------------------------------------------
    # Валидация: оба параметра обязательны
    # ------------------------------------------------------------
    if not isinstance(office_id, str) or not office_id.strip():
        return err(
            code="validation_error",
            error="Параметр office_id обязателен и не должен быть пустым.",
        )

    if not isinstance(office_address, str) or not office_address.strip():
        return err(
            code="validation_error",
            error="Параметр office_address обязателен и не должен быть пустым.",
        )

    # ------------------------------------------------------------
    # Фиксация выбора (state)
    # ------------------------------------------------------------
    return ok(
        {
            "office_id": office_id,
            "office_address": office_address,
        }
    )
