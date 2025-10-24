import os
from fastmcp import FastMCP

from ..tools.faq import tool_faq
from ..tools.services import tool_services
from ..tools.product_id import tool_record_product_id
from ..tools.record_time import tool_record_time
from ..tools.product_search_sofia import tool_product_search
from ..tools.available_time_for_master import tool_available_time_for_master


MCP_PORT_SOFIA = int(os.getenv("MCP_PORT_SOFIA"))  # 4012

mcp = FastMCP(name="Sofia")

mcp.mount(tool_faq, 'zena')
mcp.mount(tool_services, 'zena')
mcp.mount(tool_product_search, 'zena')
mcp.mount(tool_record_product_id, 'zena')
mcp.mount(tool_available_time_for_master, 'zena')
mcp.mount(tool_record_time, 'zena')


if __name__ == "__main__":
    mcp.run(transport="sse", port=MCP_PORT_SOFIA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_sofia

# ss -tulnp | grep :4002
# sudo fuser -k 4001/tcp
# sudo kill -9 1287533