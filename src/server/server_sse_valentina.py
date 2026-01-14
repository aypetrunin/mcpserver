"""Модуль сборки MCP-сервера для фирмы Sofia."""

import os

from fastmcp import FastMCP

from ..tools.faq import tool_faq  # type: ignore
from ..tools.services import tool_services  # type: ignore
from ..tools.record_time import tool_record_time  # type: ignore
from ..tools.recommendations import tool_recommendations  # type: ignore
from ..tools.remember_office import tool_remember_office  # type: ignore
from ..tools.remember_product_id import tool_remember_product_id  # type: ignore
from ..tools.remember_desired_date import tool_remember_desired_date  # type: ignore
from ..tools.remember_desired_time import tool_remember_desired_time  # type: ignore
from ..tools.avaliable_time_for_master import tool_avaliable_time_for_master  # type: ignore
from ..tools.class_product_search_full import MCPSearchProductFull  # type: ignor

MCP_PORT_VALENTINA = os.getenv("MCP_PORT_VALENTINA")  # 5002
CHANNEL_IDS_VALENTINA =  [item.strip() for item in os.getenv("CHANNEL_IDS_VALENTINA").split(",")]  # 21

print(f"CHANNEL_ID_SOFIA: {CHANNEL_IDS_VALENTINA}")

tool_product_search_sofia = MCPSearchProductFull(channel_ids=CHANNEL_IDS_VALENTINA).get_tool()

mcp_valentina = FastMCP(name="Valentina")

mcp_valentina.mount(tool_faq, "zena")
mcp_valentina.mount(tool_services, "zena")
mcp_valentina.mount(tool_record_time, "zena")
mcp_valentina.mount(tool_remember_office, "zena")
mcp_valentina.mount(tool_recommendations, "zena")
mcp_valentina.mount(tool_remember_product_id, "zena")
mcp_valentina.mount(tool_product_search_sofia, "zena")
mcp_valentina.mount(tool_remember_desired_date, "zena")
mcp_valentina.mount(tool_remember_desired_time, "zena")
mcp_valentina.mount(tool_avaliable_time_for_master, "zena")

if __name__ == "__main__":
    mcp_valentina.run(transport="sse", port=int(MCP_PORT_VALENTINA), host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_sofia

# ss -tulnp | grep :4002
# sudo fuser -k 4001/tcp
# sudo kill -9 1287533
