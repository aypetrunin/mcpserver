"""MCP-сервер для фиксации выбранного клиентом филиала."""

from typing import Any

from fastmcp import FastMCP


tool_remember_office = FastMCP(name="remember_office")


@tool_remember_office.tool(
    name="remember_office",
    description=(
        "Сохраняет выбранный клиентом филиал для записи.\n\n"
        "**Args:**\n"
        "- office_id (`str`, required): ID филиала.\n"
        "- office_address (`str`, required): Адрес филиала.\n\n"
        "**Returns:**\n"
        "- `dict`: {success: bool, office_id: str, office_address: str}\n\n"
        "**Примеры:**\n"
        '1) Клиент: "Запиши на Ленина на завтра в 10"\n'
        "   Вход:\n"
        '   {"office_id": "192", "office_address": "пр. Ленина, 2"}\n\n'
        '2) Клиент: "Хочу на Мира"\n'
        "   Вход:\n"
        '   {"office_id": "10", "office_address": "ул. Мира, 21"}\n'
    ),
)
async def remember_office(
    office_id: str,
    office_address: str,
) -> dict[str, Any]:
    """Сохранить выбранный клиентом филиал для записи."""
    return {
        "success": True,
        "office_id": office_id,
        "office_address": office_address,
    }
