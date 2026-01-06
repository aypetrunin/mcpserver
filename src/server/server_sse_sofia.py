"""Модуль сборки MCP-сервера для фирмы Sofia."""

import os

from fastmcp import FastMCP

from ..tools.faq import tool_faq  # type: ignore
from ..tools.services import tool_services  # type: ignore
from ..tools.record_time import tool_record_time  # type: ignore
from ..tools.recommendations import tool_recommendations  # type: ignore
from ..tools.remember_product_id import tool_remember_product_id  # type: ignore
from ..tools.avaliable_time_for_master import tool_avaliable_time_for_master  # type: ignore
from ..tools.class_product_search_full import MCPSearchProductFull  # type: ignore


MCP_PORT_SOFIA = os.getenv("MCP_PORT_SOFIA")  # 5002
CHANNEL_IDS_SOFIA =  [item.strip() for item in os.getenv("CHANNEL_IDS_SOFIA").split(",")]  # 1, 19

print(f"CHANNEL_ID_SOFIA: {CHANNEL_IDS_SOFIA}")

tool_product_search_sofia = MCPSearchProductFull(channel_ids=CHANNEL_IDS_SOFIA).get_tool()

mcp_sofia = FastMCP(name="Sofia")

mcp_sofia.mount(tool_faq, "zena")
mcp_sofia.mount(tool_services, "zena")
mcp_sofia.mount(tool_record_time, "zena")
mcp_sofia.mount(tool_recommendations, "zena")
mcp_sofia.mount(tool_remember_product_id, "zena")
mcp_sofia.mount(tool_product_search_sofia, "zena")
mcp_sofia.mount(tool_avaliable_time_for_master, "zena")


if __name__ == "__main__":
    mcp_sofia.run(transport="sse", port=int(MCP_PORT_SOFIA), host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_sofia

# ss -tulnp | grep :4002
# sudo fuser -k 4001/tcp
# sudo kill -9 1287533
