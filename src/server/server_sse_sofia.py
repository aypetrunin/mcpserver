"""Модуль сборки MCP-сервера для фирмы Sofia."""

import os

from fastmcp import FastMCP

from ..tools.avaliable_time_for_master import tool_avaliable_time_for_master  # type: ignore
from ..tools.class_product_search_full import MCPSearchProductFull, build_product_search_tool  # type: ignore
from ..tools.faq import tool_faq  # type: ignore
from ..tools.remember_product_id import tool_remember_product_id  # type: ignore
# from ..tools.remember_product_id_list import tool_remember_product_id_list  # type: ignore
from ..tools.record_time import tool_record_time  # type: ignore
from ..tools.services import tool_services  # type: ignore

MCP_PORT_SOFIA = os.getenv("MCP_PORT_SOFIA")  # 5002
CHANNEL_ID_SOFIA = os.getenv("CHANNEL_ID_SOFIA")  # 1

print(f"CHANNEL_ID_SOFIA: {CHANNEL_ID_SOFIA}")

tool_product_search_sofia = build_product_search_tool(CHANNEL_ID_SOFIA)
# mcp.mount(tool_product_search_sofia, "zena/sofia")

# product_search_sofia = MCPSearchProductFull(channel_id='1')
# tool_product_search_sofia = product_search_sofia.get_tool()

mcp_sofia = FastMCP(name="Sofia")

mcp_sofia.mount(tool_faq, "zena")
mcp_sofia.mount(tool_services, "zena")
mcp_sofia.mount(tool_record_time, "zena")
mcp_sofia.mount(tool_product_search_sofia, "zena")
mcp_sofia.mount(tool_remember_product_id, "zena")
mcp_sofia.mount(tool_avaliable_time_for_master, "zena")


if __name__ == "__main__":
    mcp_sofia.run(transport="sse", port=MCP_PORT_SOFIA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_sofia

# ss -tulnp | grep :4002
# sudo fuser -k 4001/tcp
# sudo kill -9 1287533
