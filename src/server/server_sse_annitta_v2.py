"""
Модуль сборки MCP-сервера для фирмы Annitta.

ВАЖНО:
- Никаких чтений env, print, создания клиентов на уровне модуля.
- Всё делаем внутри функций (factory-подход).
"""

from fastmcp import FastMCP

from .server_common import build_mcp, get_env_csv, run_standalone

from ..tools.faq import tool_faq  # type: ignore
from ..tools.services import tool_services  # type: ignore
from ..tools.record_time import tool_record_time  # type: ignore
from ..tools.remember_master import tool_remember_master  # type: ignore
from ..tools.remember_product_id import tool_remember_product_id  # type: ignore
from ..tools.class_avaliable_time_for_master import MCPAvailableTimeForMaster  # type: ignore
from ..tools.class_product_search_query import MCPSearchProductQuery  # type: ignore


async def build_mcp_annitta() -> FastMCP:
    """
    Собираем и возвращаем FastMCP сервер для Annitta.
    Ничего не запускаем тут, только создаём объект.
    """

    channel_name = 'annitta'
    channel_ids = get_env_csv("CHANNEL_IDS_ANNITTA")
 
    m = MCPSearchProductQuery(channel_ids=channel_ids)
    tool_product_search_annitta = m.get_tool()

    a = await MCPAvailableTimeForMaster.create(server_name=channel_name, channel_ids=channel_ids)
    tool_avaliable_time_for_master = a.get_tool()

    return build_mcp(
        name=channel_name,
        mounts=[
            (tool_faq, "zena"),
            (tool_services, "zena"),
            (tool_record_time, "zena"),
            (tool_remember_master, "zena"),
            (tool_remember_product_id, "zena"),
            (tool_product_search_annitta, "zena"),
            (tool_avaliable_time_for_master, "zena"),
        ],
    )


if __name__ == "__main__":
    run_standalone(
        build=build_mcp_annitta,
        port_env="MCP_PORT_ANNITTA",
        defaults={
            "MCP_PORT_ANNITTA": "5006",
            "CHANNEL_IDS_ANNITTA": "6",
        },
        print_tools=True,
    )


# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run --active python -m src.server.server_sse_annitta_v2
