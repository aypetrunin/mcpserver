"""tenant_anastasia.py — сборка списка tools для tenant'а Anastasia.

ВАЖНО:
- Никаких чтений env, print, создания клиентов на уровне модуля.
- Всё делаем внутри функций (factory-подход).
- Namespace ("zena") здесь не используется: он задаётся централизованно в server_registry.py.
"""

from typing import Any

from ..tools.class_avaliable_time_for_master_list import MCPAvailableTimeForMasterList
from ..tools.faq import tool_faq
from ..tools.recommendations import tool_recommendations
from ..tools.record_time import tool_record_time
from ..tools.remember_master import tool_remember_master
from ..tools.remember_product_id_list import tool_remember_product_id_list
from ..tools.services import tool_services


Tool = Any


async def build_tools_anastasia(server_name: str, channel_ids: list[str]) -> list[Tool]:
    """Собирает список tools для tenant'а Anastasia.

    channel_ids не используются, но оставлены для единого интерфейса.
    """
    _ = channel_ids

    available_time_builder = await MCPAvailableTimeForMasterList.create(
        server_name=server_name,
    )
    tool_available_time_for_master_list = available_time_builder.get_tool()

    return [
        tool_faq,
        tool_services,
        tool_record_time,
        tool_remember_master,
        tool_recommendations,
        tool_remember_product_id_list,
        tool_available_time_for_master_list,
    ]
