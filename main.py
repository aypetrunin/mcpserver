import os
import asyncio

from dotenv import load_dotenv



from src.server.server_sse_alisa import mcp as mcp_alisa
from src.server.server_sse_sofia import mcp as mcp_sofia
from src.server.server_sse_anisa import mcp as mcp_anisa
from src.server.server_sse_annitta import mcp as mcp_annitta
from src.server.server_sse_anastasia import mcp as mcp_anastasia

load_dotenv()

MCP_PORT_ALISA = int(os.getenv("MCP_PORT_ALISA"))  # 5001
MCP_PORT_SOFIA = int(os.getenv("MCP_PORT_SOFIA"))  # 5002
MCP_PORT_ANISA = int(os.getenv("MCP_PORT_ANISA"))  # 5005
MCP_PORT_ANNITTA = int(os.getenv("MCP_PORT_ANNITTA"))  # 5006
MCP_PORT_ANASTASIA = int(os.getenv("MCP_PORT_ANASTASIA"))  # 5007


async def main():
    await asyncio.gather(
        mcp_alisa.run_async(transport="sse", port=MCP_PORT_ALISA, host="0.0.0.0"),
        mcp_sofia.run_async(transport="sse", port=MCP_PORT_SOFIA, host="0.0.0.0"),
        mcp_anisa.run_async(transport="sse", port=MCP_PORT_ANISA, host="0.0.0.0"),
        mcp_annitta.run_async(transport="sse", port=MCP_PORT_ANNITTA, host="0.0.0.0"),
        mcp_anastasia.run_async(transport="sse", port=MCP_PORT_ANASTASIA, host="0.0.0.0"),
    )

if __name__ == "__main__":
    asyncio.run(main())
