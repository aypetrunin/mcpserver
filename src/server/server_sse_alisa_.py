import os
from fastmcp import FastMCP

from ..tools.faq import tool_faq
from ..tools.services import tool_services
from ..tools.product_search_alisa import tool_product_search
from ..tools.product_id import tool_record_product_id
from ..tools.available_time_for_master import tool_available_time_for_master
from ..tools.record_time import tool_record_time
# from .server_mcp.mcp_services import mcp_services
# from .server_mcp.mcp_yclients_record_time import mcp_record_time
# # from .server_mcp.mcp_product_id_and_available_time import mcp_record_product_id_and_available_time
# # from .server_mcp.mcp_yclients_available_time import mcp_available_time
# from .server_mcp.mcp_yclients_available_time_for_master import mcp_available_time_for_master
# from .server_mcp.mcp_product_search_alisa import mcp_product_search
# from .server_mcp.mcp_product_id import mcp_record_product_id

MCP_PORT_ALISA = int(os.getenv("MCP_PORT_ALISA"))

mcp = FastMCP(name="Alisa")

mcp.mount(tool_faq, 'zena')
mcp.mount(tool_services, 'zena')
mcp.mount(tool_product_search, 'zena')
mcp.mount(tool_record_product_id, 'zena')
mcp.mount(tool_available_time_for_master, 'zena')
mcp.mount(tool_record_time, 'zena')


if __name__ == "__main__":
    mcp.run(transport="sse", port=MCP_PORT_ALISA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_alisa
