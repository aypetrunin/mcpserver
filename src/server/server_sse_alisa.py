"""Модуль сборки MCP-сервера для фирмы Алиса."""

import os

from fastmcp import FastMCP

from ..tools.available_time_for_master import tool_available_time_for_master
from ..tools.faq import tool_faq
from ..tools.product_id import tool_record_product_id
from ..tools.product_search_full import tool_product_search
from ..tools.record_time import tool_record_time
from ..tools.services import tool_services

MCP_PORT_ALISA = int(os.getenv("MCP_PORT_ALISA"))  # 5001

mcp = FastMCP(name="Alisa")

mcp.mount(tool_faq, "zena")
mcp.mount(tool_services, "zena")
mcp.mount(tool_record_time, "zena")
mcp.mount(tool_product_search, "zena")
mcp.mount(tool_record_product_id, "zena")
mcp.mount(tool_available_time_for_master, "zena")


if __name__ == "__main__":
    mcp.run(transport="sse", port=MCP_PORT_ALISA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_alisa
