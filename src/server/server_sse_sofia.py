"""Модуль сборки MCP-сервера для фирмы Sofia."""

import os

from fastmcp import FastMCP

from ..tools.available_time_for_master import tool_available_time_for_master
from ..tools.class_product_search_full import MCPSearchProductFull
from ..tools.faq import tool_faq
from ..tools.product_id import tool_record_product_id
from ..tools.record_time import tool_record_time
from ..tools.services import tool_services

MCP_PORT_SOFIA = int(os.getenv("MCP_PORT_SOFIA"))  # 5002
CHANNEL_ID_SOFIA = int(os.getenv("CHANNEL_ID_SOFIA"))  # 1

product_search = MCPSearchProductFull(channel_id=CHANNEL_ID_SOFIA)
tool_product_search = product_search.get_tool()

mcp = FastMCP(name="Sofia")

mcp.mount(tool_faq, "zena")
mcp.mount(tool_services, "zena")
mcp.mount(tool_record_time, "zena")
mcp.mount(tool_product_search, "zena")
mcp.mount(tool_record_product_id, "zena")
mcp.mount(tool_available_time_for_master, "zena")


if __name__ == "__main__":
    mcp.run(transport="sse", port=MCP_PORT_SOFIA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_sofia

# ss -tulnp | grep :4002
# sudo fuser -k 4001/tcp
# sudo kill -9 1287533
