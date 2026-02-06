"""tenant_marina.py — сборка списка tools для tenant'а Marina.

ВАЖНО:
- Никаких чтений env на уровне модуля.
- Никаких mounts/namespace здесь нет: только список tool-объектов.
- Namespace ("zena") задаётся централизованно в server_registry.py.
"""

from typing import Any

from ..tools.call_administrator import tool_call_administrator
from ..tools.class_avaliable_time_for_master import MCPAvailableTimeForMaster
from ..tools.class_client_records import MCPClientRecords
from ..tools.class_product_search_full import MCPSearchProductFull
from ..tools.delete_client_record import tool_record_delete
from ..tools.faq import tool_faq
from ..tools.recommendations import tool_recommendations
from ..tools.record_time import tool_record_time
from ..tools.remember_desired_date import tool_remember_desired_date
from ..tools.remember_desired_time import tool_remember_desired_time
from ..tools.remember_master import tool_remember_master
from ..tools.remember_office import tool_remember_office
from ..tools.remember_product_id import tool_remember_product_id
from ..tools.reschedule_client_record import tool_record_reschedule
from ..tools.services import tool_services


Tool = Any


async def build_tools_marina(server_name: str, channel_ids: list[str]) -> list[Tool]:
    """Собирает список tools для tenant'а Marina.

    server_name и channel_ids приходят из server_spec_factory.
    """
    product_search_builder = await MCPSearchProductFull.create(channel_ids=channel_ids)
    tool_product_search = product_search_builder.get_tool()

    records_builder = await MCPClientRecords.create(channel_ids=channel_ids)
    tool_records = records_builder.get_tool()

    available_time_builder = await MCPAvailableTimeForMaster.create(
        server_name=server_name,
        channel_ids=channel_ids,
    )
    tool_available_time = available_time_builder.get_tool()

    return [
        tool_faq,
        tool_services,
        tool_record_time,
        tool_records,
        tool_record_delete,
        tool_remember_office,
        tool_remember_master,
        tool_recommendations,
        tool_record_reschedule,
        tool_call_administrator,
        tool_remember_product_id,
        tool_product_search,
        tool_remember_desired_date,
        tool_remember_desired_time,
        tool_available_time,
    ]
