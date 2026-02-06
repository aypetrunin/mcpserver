"""MCP-сервер для поиска статистики посещений занятий клиента."""

from typing import Any

from fastmcp import FastMCP

from ..crm.crm_get_client_statistics import go_get_client_statisics  # type: ignore


tool_get_client_statistics = FastMCP(name="get_client_statistics")


@tool_get_client_statistics.tool(
    name="get_client_statistics",
    description=(
        "Получение статистики посещений занятий клиентом.\n\n"
        "**Назначение:**\n"
        "Используется для получения информации о балансе и статистике посещений "
        "занятий клиентом. Может применяться при онлайн-бронировании.\n\n"
        "**Примеры запросов:**\n"
        '- "Какой у меня баланс?"\n'
        '- "Сколько занятий у меня осталось?"\n'
        '- "Покажи статистику."\n'
        '- "Покажи баланс."\n\n'
        "**Args:**\n"
        "- phone (`str`, required): Телефон клиента.\n"
        "- channel_id (`str`, required): ID учебной организации.\n\n"
        "**Returns:**\n"
        "- `dict`: Статистика и баланс посещений клиента.\n"
    ),
)
async def get_client_statistics(
    phone: str,
    channel_id: str,
) -> dict[str, Any]:
    """Получить статистику посещений занятий клиента."""
    response = await go_get_client_statisics(
        phone=phone,
        channel_id=channel_id,
    )
    return response

