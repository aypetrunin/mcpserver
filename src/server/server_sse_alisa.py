"""Модуль сборки MCP-сервера для фирмы Алиса."""

import os

from fastmcp import FastMCP

from ..tools.faq import tool_faq  # type: ignore
from ..tools.services import tool_services  # type: ignore
from ..tools.remember_product_id import tool_remember_product_id  # type: ignore
from ..tools.record_time import tool_record_time  # type: ignore
from ..tools.class_product_search_full import MCPSearchProductFull, build_product_search_tool  # type: ignore
from ..tools.avaliable_time_for_master import tool_avaliable_time_for_master  # type: ignore

MCP_PORT_ALISA = os.getenv("MCP_PORT_ALISA")  # 5001
CHANNEL_ID_ALISA = os.getenv("CHANNEL_ID_ALISA")  # 2

tool_product_search_alisa = build_product_search_tool(CHANNEL_ID_ALISA)
# product_search_alisa = MCPSearchProductFull(channel_id='2')
# tool_product_search_alisa = product_search_alisa.get_tool()

# tool_product_search_alisa = MCPSearchProductFull(channel_id='2').get_tool()

mcp_alisa = FastMCP(name="Alisa")

mcp_alisa.mount(tool_faq, "zena")
mcp_alisa.mount(tool_services, "zena")
mcp_alisa.mount(tool_record_time, "zena")
mcp_alisa.mount(tool_product_search_alisa, "zena")
mcp_alisa.mount(tool_remember_product_id, "zena")
mcp_alisa.mount(tool_avaliable_time_for_master, "zena")


if __name__ == "__main__":
    mcp_alisa.run(transport="sse", port=MCP_PORT_ALISA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_alisa
