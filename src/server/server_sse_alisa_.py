from fastmcp import FastMCP

from ..tools.faq import tool_faq
# from .server_mcp.mcp_services import mcp_services
# from .server_mcp.mcp_yclients_record_time import mcp_record_time
# # from .server_mcp.mcp_product_id_and_available_time import mcp_record_product_id_and_available_time
# # from .server_mcp.mcp_yclients_available_time import mcp_available_time
# from .server_mcp.mcp_yclients_available_time_for_master import mcp_available_time_for_master
# from .server_mcp.mcp_product_search_alisa import mcp_product_search
# from .server_mcp.mcp_product_id import mcp_record_product_id


mcp = FastMCP(name="Alisa")

mcp.mount('zena', tool_faq)
# mcp.mount('zena', mcp_services)
# mcp.mount('zena', mcp_product_search)
# mcp.mount('zena', mcp_available_time_for_master)
# mcp.mount('zena', mcp_record_time)
# mcp.mount('zena', mcp_record_product_id)


if __name__ == "__main__":
    mcp.run(transport="sse", port=4010, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcp
# python -m src.server.server_sse_alisa
# kill 1470180
