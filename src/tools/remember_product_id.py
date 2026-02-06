"""MCP-сервер для фиксации выбранной клиентом услуги в базе данных."""

from typing import Any

from fastmcp import FastMCP

from ..postgres.postgres_util import get_product_name_for_id  # type: ignore


tool_remember_product_id = FastMCP(name="remember_product_id")


@tool_remember_product_id.tool(
    name="remember_product_id",
    description=(
        "Подтверждение выбора клиентом одной услуги.\n\n"
        "Примеры:\n"
        "- «Выбираю LPG-массаж»\n"
        "- «Запишите на эпиляцию ног»\n"
        "- «Хочу стрижку модельную»\n\n"
        "**Args:**\n"
        "- session_id (`str`, required): ID диалоговой сессии.\n"
        "- product_id (`str`, required): ID выбранной услуги (формат: 2-113323232).\n"
        "- product_name (`str`, required): Название выбранной услуги.\n\n"
        "**Returns:**\n"
        "- `dict`: {success: bool, message?: str, products?: list}\n"
    ),
)
async def remember_product_id(
    session_id: str,
    product_id: str,
    product_name: str,
) -> dict[str, Any]:
    """Зафиксировать выбранную клиентом услугу."""
    _ = session_id  # используется в контексте диалога, здесь не нужен

    fail_resp = {
        "success": False,
        "message": "Ошибка в выборе услуги. Покажи заново найденные услуги.",
    }

    product_name_for_id = await get_product_name_for_id(product_id=product_id)
    if product_name_for_id is None:
        return fail_resp

    # Нормализация для сравнения
    if product_name_for_id.strip().casefold() != product_name.strip().casefold():
        return fail_resp

    return {
        "success": True,
        "products": [{"product_id": product_id, "product_name": product_name_for_id}],
    }
