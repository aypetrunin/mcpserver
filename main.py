import os
import asyncio

from src.server.server_sse_alisa_ import mcp as mcp_alisa
# from src.server.server_sse_sofia_ import mcp as mcp_sofia


MCP_PORT_ALISA = int(os.getenv("MCP_PORT_ALISA"))
# MCP_PORT_SOFIA = int(os.getenv("MCP_PORT_SOFIA"))

async def main():
    await asyncio.gather(
        mcp_alisa.run_async(transport="sse", port=MCP_PORT_ALISA, host="0.0.0.0"),
        # mcp_sofia.run_async(transport="sse", port=MCP_PORT_SOFIA, host="0.0.0.0"),
    )


if __name__ == "__main__":
    asyncio.run(main())
