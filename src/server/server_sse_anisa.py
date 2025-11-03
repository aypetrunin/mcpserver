"""Модуль сборки MCP-сервера для фирмы Anisa."""

import os

from fastmcp import FastMCP

from ..tools.available_time_for_master import tool_available_time_for_master
from ..tools.faq import tool_faq
from ..tools.product_id import tool_record_product_id
from ..tools.product_search_anisa import tool_product_search
from ..tools.record_time import tool_record_time
from ..tools.services import tool_services

MCP_PORT_ANISA = int(os.getenv("MCP_PORT_ANISA"))  # 4015

mcp = FastMCP(name="Anisa")

mcp.mount(tool_faq, "zena")
mcp.mount(tool_services, "zena")
mcp.mount(tool_record_time, "zena")
mcp.mount(tool_product_search, "zena")
mcp.mount(tool_record_product_id, "zena")
mcp.mount(tool_available_time_for_master, "zena")


if __name__ == "__main__":
    mcp.run(transport="sse", port=MCP_PORT_ANISA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/mcp
# nohup uv run python -m zena_qdrant.server_sse_anisa &
# kill 1500178
