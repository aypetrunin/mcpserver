"""
Модуль сборки MCP-сервера для фирмы Valentina.

ВАЖНО:
- Никаких чтений env, print, создания клиентов на уровне модуля.
- Всё делаем внутри функций (factory-подход).
"""

from fastmcp import FastMCP

from .server_common import build_mcp, get_env_csv, run_standalone

from ..tools.faq import tool_faq  # type: ignore
from ..tools.services import tool_services  # type: ignore
from ..tools.record_time import tool_record_time  # type: ignore
from ..tools.recommendations import tool_recommendations  # type: ignore
from ..tools.remember_office import tool_remember_office  # type: ignore
from ..tools.remember_master import tool_remember_master  # type: ignore
from ..tools.remember_product_id import tool_remember_product_id  # type: ignore
from ..tools.remember_desired_date import tool_remember_desired_date  # type: ignore
from ..tools.remember_desired_time import tool_remember_desired_time  # type: ignore
from ..tools.avaliable_time_for_master import tool_avaliable_time_for_master  # type: ignore
from ..tools.class_product_search_full import MCPSearchProductFull  # type: ignore
from ..tools.class_client_records import MCPClientRecords
from ..tools.delete_client_record import tool_record_delete  # type: ignore
from ..tools.reschedule_client_record import tool_record_reschedule  # type: ignore
from ..tools.call_administrator import tool_call_administrator  # type: ignore

async def build_mcp_valentina() -> FastMCP:
    """
    Собираем и возвращаем FastMCP сервер для Valentina.
    Ничего не запускаем тут, только создаём объект.
    """
    channel_ids = get_env_csv("CHANNEL_IDS_VALENTINA")

    # tool для product search, зависящий от channel_ids
    m = await MCPSearchProductFull.create(channel_ids=channel_ids)
    tool_product_search_valentina = m.get_tool()

    r = await MCPClientRecords.create(channel_ids=channel_ids)
    tool_records_valentina = r.get_tool()

    return build_mcp(
        name="Valentina",
        mounts=[
            (tool_faq, "zena"),
            (tool_services, "zena"),
            (tool_record_time, "zena"),
            (tool_record_delete, "zena"),
            (tool_recommendations, "zena"),
            (tool_remember_office, "zena"),
            (tool_remember_master, "zena"),
            (tool_record_reschedule, "zena"),
            (tool_call_administrator, "zena"),
            (tool_records_valentina, "zena"),
            (tool_remember_product_id, "zena"),
            (tool_product_search_valentina, "zena"),
            (tool_remember_desired_date, "zena"),
            (tool_remember_desired_time, "zena"),
            (tool_avaliable_time_for_master, "zena"),
        ],
    )


if __name__ == "__main__":

    run_standalone(
        build=build_mcp_valentina,
        port_env="MCP_PORT_VALENTINA",
        defaults={
            "MCP_PORT_VALENTINA": "5099",
            "CHANNEL_IDS_VALENTINA": "21",
        },
        print_tools=True,
    )


# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run --active python -m src.server.server_sse_valentina_v2
