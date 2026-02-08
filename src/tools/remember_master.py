"""MCP-сервер для фиксации выбранного клиентом мастера.

State-tool: сохраняет выбор пользователя в состоянии диалога.
"""

from __future__ import annotations

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok


tool_remember_master = FastMCP(name="remember_master")


@tool_remember_master.tool(
    name="remember_master",
    description=(
        "Сохраняет выбранного клиентом мастера для записи.\n\n"
        "**Args:**\n"
        "- master_id (`str`, required): ID мастера.\n"
        "- master_name (`str`, required): Имя мастера.\n\n"
        "**Returns:**\n"
        "- Payload[dict]\n\n"
        "**Примеры:**\n"
        '1) Клиент: "Запиши меня к Ивановой"\n'
        '   Вход: {"master_id": "6326437", "master_name": "Иванова Валентина"}\n\n'
        '2) Клиент: "Когда есть время у Марины"\n'
        '   Вход: {"master_id": "546758", "master_name": "Николаева Марина"}\n'
    ),
)
async def remember_master(
    master_id: str,
    master_name: str,
) -> Payload[dict[str, str]]:
    """
    Описание результата.

    Контракт:
    - ok(data)  — мастер валиден и зафиксирован
    - err(...)  — ошибка валидации
    """
    # ------------------------------------------------------------
    # Валидация: оба параметра обязательны
    # ------------------------------------------------------------
    if not isinstance(master_id, str) or not master_id.strip():
        return err(
            code="validation_error",
            error="Параметр master_id обязателен и не должен быть пустым.",
        )

    if not isinstance(master_name, str) or not master_name.strip():
        return err(
            code="validation_error",
            error="Параметр master_name обязателен и не должен быть пустым.",
        )

    # ------------------------------------------------------------
    # Фиксация выбора (state)
    # ------------------------------------------------------------
    return ok(
        {
            "master_id": master_id,
            "master_name": master_name,
        }
    )
