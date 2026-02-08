"""MCP-сервер для фиксации выбранных клиентом услуг.

State-tool: сохраняет выбор пользователя в состоянии диалога.
"""

from __future__ import annotations

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok


tool_remember_product_id_list = FastMCP(name="remember_product_id_list")


@tool_remember_product_id_list.tool(
    name="remember_product_id_list",
    description=(
        "Фиксация выбранной клиентом услуги или списка услуг.\n\n"
        "Примеры:\n"
        "- «Выбираю LPG-массаж»\n"
        "- «Запишите на эпиляцию ног»\n"
        "- «Хочу прессотерапию и роликовый массажёр»\n\n"
        "**Args:**\n"
        "- session_id (`str`, required): ID диалоговой сессии.\n"
        "- product_id (`list[str]`, required): Список ID услуг (формат: 2-113323232).\n"
        "- product_name (`list[str]`, required): Список названий услуг.\n\n"
        "**Returns:**\n"
        "- Payload[list[dict]]\n"
    ),
)
async def remember_product_id(
    session_id: str,
    product_id: list[str],
    product_name: list[str],
) -> Payload[list[dict[str, str]]]:
    """
    Описание результата.

    Контракт:
    - ok(data)  — услуги валидны и зафиксированы
    - err(...)  — ошибка валидации
    """
    # ------------------------------------------------------------
    # session_id — нужен для контекста, но здесь не используется
    # ------------------------------------------------------------
    if not isinstance(session_id, str) or not session_id.strip():
        return err(
            code="validation_error",
            error="Параметр session_id обязателен и не должен быть пустым.",
        )

    # ------------------------------------------------------------
    # Валидация списков
    # ------------------------------------------------------------
    if not isinstance(product_id, list) or not isinstance(product_name, list):
        return err(
            code="validation_error",
            error="product_id и product_name должны быть списками.",
        )

    if not product_id or not product_name:
        return err(
            code="validation_error",
            error="Списки product_id и product_name не должны быть пустыми.",
        )

    if len(product_id) != len(product_name):
        return err(
            code="validation_error",
            error="product_id и product_name должны быть одинаковой длины.",
        )

    # ------------------------------------------------------------
    # Формирование списка услуг
    # ------------------------------------------------------------
    items: list[dict[str, str]] = []

    for pid, pname in zip(product_id, product_name):
        if not isinstance(pid, str) or not pid.strip():
            return err(
                code="validation_error",
                error="Каждый product_id должен быть непустой строкой.",
            )
        if not isinstance(pname, str) or not pname.strip():
            return err(
                code="validation_error",
                error="Каждый product_name должен быть непустой строкой.",
            )

        items.append(
            {
                "product_id": pid,
                "product_name": pname,
            }
        )

    # ------------------------------------------------------------
    # Фиксация выбора (state)
    # ------------------------------------------------------------
    return ok(items)
