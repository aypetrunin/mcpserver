"""tenant_anisa.py — сборка списка tools для tenant'а Anisa.

ВАЖНО:
- Никаких чтений env, print, создания клиентов на уровне модуля.
- Всё делаем внутри функций (factory-подход).
- Namespace ("zena") здесь не используется: он задаётся централизованно в server_registry.py.
"""

from typing import Any

from ..tools.class_avaliable_time_for_master import MCPAvailableTimeForMaster
from ..tools.class_product_search_query import MCPSearchProductQuery
from ..tools.faq import tool_faq
from ..tools.record_time import tool_record_time
from ..tools.remember_master import tool_remember_master
from ..tools.remember_product_id import tool_remember_product_id
from ..tools.services import tool_services


Tool = Any


async def build_tools_anisa(server_name: str, channel_ids: list[str]) -> list[Tool]:
    """Собирает список tools для tenant'а Anisa.

    Ничего не запускаем тут, только создаём tool-объекты.
    """
    product_search_builder = MCPSearchProductQuery(channel_ids=channel_ids)
    tool_product_search = product_search_builder.get_tool()

    available_time_builder = await MCPAvailableTimeForMaster.create(
        server_name=server_name,
        channel_ids=channel_ids,
    )
    tool_available_time_for_master = available_time_builder.get_tool()

    return [
        tool_faq,
        tool_services,
        tool_record_time,
        tool_remember_master,
        tool_remember_product_id,
        tool_product_search,
        tool_available_time_for_master,
    ]
