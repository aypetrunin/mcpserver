"""Модуль сборки MCP-сервера для фирмы Алиса."""

import os

from fastmcp import FastMCP

from ..tools.faq import tool_faq  # type: ignore
from ..tools.services import tool_services  # type: ignore
from ..tools.record_time import tool_record_time  # type: ignore
from ..tools.remember_master import tool_remember_master  # type: ignore
from ..tools.remember_product_id import tool_remember_product_id  # type: ignore
from ..tools.avaliable_time_for_master import tool_avaliable_time_for_master  # type: ignore
from ..tools.class_product_search_full import MCPSearchProductFull  # type: ignore


MCP_PORT_ALISA = os.getenv("MCP_PORT_ALISA")  # 5001
CHANNEL_IDS_ALISA = [item.strip() for item in os.getenv("CHANNEL_IDS_ALISA").split(",")] # 2

tool_product_search_alisa = MCPSearchProductFull(channel_ids=CHANNEL_IDS_ALISA).get_tool()

mcp_alisa = FastMCP(name="Alisa")

mcp_alisa.mount(tool_faq, "zena")
mcp_alisa.mount(tool_services, "zena")
mcp_alisa.mount(tool_record_time, "zena")
mcp_alisa.mount(tool_remember_master, "zena")
mcp_alisa.mount(tool_product_search_alisa, "zena")
mcp_alisa.mount(tool_remember_product_id, "zena")
mcp_alisa.mount(tool_avaliable_time_for_master, "zena")


if __name__ == "__main__":
    mcp_alisa.run(transport="sse", port=MCP_PORT_ALISA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_alisa
