"""Модуль сборки MCP-сервера для фирмы Anastasia."""

import os

from fastmcp import FastMCP

from ..tools.avaliable_time_for_master_list import tool_avaliable_time_for_master_list  # type: ignore
from ..tools.class_product_search_full import MCPSearchProductFull  # type: ignore
from ..tools.faq import tool_faq  # type: ignore
from ..tools.remember_product_id_list import tool_remember_product_id_list  # type: ignore
from ..tools.record_time import tool_record_time  # type: ignore
from ..tools.services import tool_services  # type: ignore
from ..tools.recommendations import tool_recommendations  # type: ignore

MCP_PORT_ANASTASIA = os.getenv("MCP_PORT_ANASTASIA")  # 5007
CHANNEL_IDS_ANASTASIA = [item.strip() for item in os.getenv("CHANNEL_IDS_ANASTASIA").split(",")]  # 7

tool_product_search = MCPSearchProductFull(channel_ids=CHANNEL_IDS_ANASTASIA).get_tool()

mcp_anastasia = FastMCP(name="Anastasia")

mcp_anastasia.mount(tool_faq, "zena")
mcp_anastasia.mount(tool_services, "zena")
mcp_anastasia.mount(tool_record_time, "zena")
mcp_anastasia.mount(tool_product_search, "zena")
mcp_anastasia.mount(tool_recommendations, "zena")
mcp_anastasia.mount(tool_remember_product_id_list, "zena")
mcp_anastasia.mount(tool_avaliable_time_for_master_list, "zena")


if __name__ == "__main__":
    mcp_anastasia.run(transport="sse", port=MCP_PORT_ANASTASIA, host="0.0.0.0")
