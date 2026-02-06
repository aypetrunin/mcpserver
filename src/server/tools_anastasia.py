"""
tenant_anastasia.py — сборка списка tools для tenant'а Anastasia.

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
from ..tools.recommendations import tool_recommendations  # type: ignore
from ..tools.remember_product_id_list import tool_remember_product_id_list  # type: ignore
from ..tools.class_avaliable_time_for_master_list import MCPAvailableTimeForMasterList  # type: ignore

Tool = Any


async def build_tools_anastasia(server_name: str, channel_ids: list[str]) -> list[Tool]:
    """
    Собираем список tools для Anastasia.
    channel_ids не используются, но оставлены для единого интерфейса.
    """

    a = await MCPAvailableTimeForMasterList.create(server_name=server_name)
    tool_available_time_for_master_list = a.get_tool()

    return [
        tool_faq,
        tool_services,
        tool_record_time,
        tool_remember_master,
        tool_recommendations,
        tool_remember_product_id_list,
        tool_available_time_for_master_list,
    ]
