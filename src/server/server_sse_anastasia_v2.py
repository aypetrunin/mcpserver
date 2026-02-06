"""
Модуль сборки MCP-сервера для фирмы Anastasia.

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
from ..tools.recommendations import tool_recommendations  # type: ignore
from ..tools.remember_product_id_list import tool_remember_product_id_list  # type: ignore
from ..tools.class_avaliable_time_for_master_list import MCPAvailableTimeForMasterList


async def build_mcp_anastasia() -> FastMCP:
    """
    Собираем и возвращаем FastMCP сервер для Anastasia.
    Ничего не запускаем тут, только создаём объект.
    """

    channel_name = 'sofia'

    a = await MCPAvailableTimeForMasterList.create(server_name=channel_name)
    tool_avaliable_time_for_master_list = a.get_tool()

    return build_mcp(
        name="Anastasia",
        mounts=[
            (tool_faq, "zena"),
            (tool_services, "zena"),
            (tool_record_time, "zena"),
            (tool_remember_master, "zena"),
            (tool_recommendations, "zena"),
            (tool_remember_product_id_list, "zena"),
            (tool_avaliable_time_for_master_list, "zena"),
        ],
    )
