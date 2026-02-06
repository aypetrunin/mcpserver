"""MCP-сервер для фиксации выбранных клиентом услуг в базе данных."""

from typing import Any

from fastmcp import FastMCP


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
        "- `list[dict]`: Список выбранных услуг (product_id + product_name).\n"
    ),
)
async def remember_product_id(
    session_id: str,
    product_id: list[str],
    product_name: list[str],
) -> list[dict[str, Any]]:
    """Зафиксировать выбранные клиентом услуги."""
    _ = session_id  # используется в контексте диалога, здесь не нужен

    return [
        {"product_id": pid, "product_name": pname}
        for pid, pname in zip(product_id, product_name)
    ]
