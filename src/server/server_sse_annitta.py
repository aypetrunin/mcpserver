"""Модуль сборки MCP-сервера для фирмы Annitta."""

import os

from fastmcp import FastMCP

from ..tools.avaliable_time_for_master import tool_avaliable_time_for_master
from ..tools.class_product_search_query import MCPSearchProductQuery
from ..tools.faq import tool_faq
from ..tools.product_id import tool_record_product_id
from ..tools.record_time import tool_record_time
from ..tools.services import tool_services

MCP_PORT_ANNITTA = int(os.getenv("MCP_PORT_ANNITTA"))  # 5006
CHANNEL_ID_ANNITTA = int(os.getenv("CHANNEL_ID_ANNITTA"))  # 6

tool_product_search = MCPSearchProductQuery(channel_id=CHANNEL_ID_ANNITTA).get_tool()

mcp = FastMCP(name="Annitta")

mcp.mount(tool_faq, "zena")
mcp.mount(tool_services, "zena")
mcp.mount(tool_record_time, "zena")
mcp.mount(tool_product_search, "zena")
mcp.mount(tool_record_product_id, "zena")
mcp.mount(tool_avaliable_time_for_master, "zena")


if __name__ == "__main__":
    mcp.run(transport="sse", port=MCP_PORT_ANNITTA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/mcp
# nohup uv run python -m zena_qdrant.server_sse_annitta &
# kill 1504239
