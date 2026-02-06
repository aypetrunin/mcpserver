"""
tenant_annitta.py — сборка списка tools для tenant'а Annitta.

ВАЖНО:
- Никаких чтений env, print, создания клиентов на уровне модуля.
- Всё делаем внутри функций (factory-подход).
- Namespace ("zena") здесь не используется: он задаётся централизованно в server_registry.py.
"""

from typing import Any

from ..tools.faq import tool_faq  # type: ignore
from ..tools.services import tool_services  # type: ignore
from ..tools.record_time import tool_record_time  # type: ignore
from ..tools.remember_master import tool_remember_master  # type: ignore
from ..tools.remember_product_id import tool_remember_product_id  # type: ignore

from ..tools.class_avaliable_time_for_master import MCPAvailableTimeForMaster  # type: ignore
from ..tools.class_product_search_query import MCPSearchProductQuery  # type: ignore

Tool = Any


async def build_tools_annitta(server_name: str, channel_ids: list[str]) -> list[Tool]:
    """
    Собираем список tools для Annitta.
    Ничего не запускаем тут, только создаём tool-объекты.
    """

    # product search (sync-конструктор — как было в исходном коде)
    m = MCPSearchProductQuery(channel_ids=channel_ids)
    tool_product_search = m.get_tool()

    a = await MCPAvailableTimeForMaster.create(
        server_name=server_name,
        channel_ids=channel_ids,
    )
    tool_available_time_for_master = a.get_tool()

    return [
        tool_faq,
        tool_services,
        tool_record_time,
        tool_remember_master,
        tool_remember_product_id,
        tool_product_search,
        tool_available_time_for_master,
    ]
