from fastmcp import FastMCP
import asyncio

from ..tools.faq import tool_faq
# from .server_mcp.mcp_services import mcp_services
# from .server_mcp.mcp_yclients_record_time import mcp_record_time
# # from .server_mcp.mcp_product_id_and_available_time import mcp_record_product_id_and_available_time
# # from .server_mcp.mcp_yclients_available_time import mcp_available_time
# from .server_mcp.mcp_yclients_available_time_for_master import mcp_available_time_for_master
# from .server_mcp.mcp_product_search_alisa import mcp_product_search
# from .server_mcp.mcp_product_id import mcp_record_product_id


# mcp = FastMCP(name="Alisa")

# mcp.mount('zena', tool_faq)
# mcp.mount('zena', mcp_services)
# mcp.mount('zena', mcp_product_search)
# mcp.mount('zena', mcp_available_time_for_master)
# mcp.mount('zena', mcp_record_time)
# mcp.mount('zena', mcp_record_product_id)


if __name__ == "__main__":

    async def main():
        mcp = FastMCP(name="Alisa")

        mcp.mount('zena', tool_faq)

        server_task = asyncio.create_task(
            mcp.run_async(transport="sse", port=4010, host="127.0.0.1")
        )
        
        await asyncio.sleep(3)

        server_task.cancel()
        
        try:
            await server_task
        except asyncio.CancelledError:
            print("Server task cancelled")

    asyncio.run(main())

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# python -m src.server.server_sse_alisa
# uv run python -m src.server.server_sse_alisa
# kill 1470180
