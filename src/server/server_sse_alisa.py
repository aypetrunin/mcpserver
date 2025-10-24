import os
from fastmcp import FastMCP

from ..tools.faq import tool_faq
from ..tools.services import tool_services
from ..tools.product_id import tool_record_product_id
from ..tools.record_time import tool_record_time
from ..tools.product_search_alisa import tool_product_search
from ..tools.available_time_for_master import tool_available_time_for_master


MCP_PORT_ALISA = int(os.getenv("MCP_PORT_ALISA"))  # 4011

mcp = FastMCP(name="Alisa")

mcp.mount(tool_faq, 'zena')
mcp.mount(tool_services, 'zena')
mcp.mount(tool_record_time, 'zena')
mcp.mount(tool_product_search, 'zena')
mcp.mount(tool_record_product_id, 'zena')
mcp.mount(tool_available_time_for_master, 'zena')



if __name__ == "__main__":
    mcp.run(transport="sse", port=MCP_PORT_ALISA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_alisa
