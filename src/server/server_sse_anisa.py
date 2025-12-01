"""Модуль сборки MCP-сервера для фирмы Anisa."""

import os

from fastmcp import FastMCP

from ..tools.avaliable_time_for_master import tool_avaliable_time_for_master  # type: ignore
from ..tools.class_product_search_query import MCPSearchProductQuery  # type: ignore
from ..tools.faq import tool_faq  # type: ignore
from ..tools.product_id import tool_record_product_id  # type: ignore
from ..tools.record_time import tool_record_time  # type: ignore
from ..tools.services import tool_services  # type: ignore

MCP_PORT_ANISA = os.getenv("MCP_PORT_ANISA")  # 5005
CHANNEL_ID_ANISA = os.getenv("CHANNEL_ID_ANISA")  # 5

tool_product_search = MCPSearchProductQuery(channel_id=CHANNEL_ID_ANISA).get_tool()

mcp = FastMCP(name="Anisa")

mcp.mount(tool_faq, "zena")
mcp.mount(tool_services, "zena")
mcp.mount(tool_record_time, "zena")
mcp.mount(tool_product_search, "zena")
mcp.mount(tool_record_product_id, "zena")
mcp.mount(tool_avaliable_time_for_master, "zena")


if __name__ == "__main__":
    mcp.run(transport="sse", port=MCP_PORT_ANISA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/mcp
# nohup uv run python -m zena_qdrant.server_sse_anisa &
# kill 1500178
