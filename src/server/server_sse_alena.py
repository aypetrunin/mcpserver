"""Модуль сборки MCP-сервера для фирмы Алена."""

import os

from fastmcp import FastMCP

from ..tools.faq import tool_faq  # type: ignore
from ..tools.lesson_id import tool_remember_lesson_id  # type: ignore
from ..tools.get_client_lessons import tool_get_client_lessons  # type: ignore
from ..tools.update_client_info import tool_update_client_info  # type: ignore
from ..tools.update_client_lesson import tool_update_client_lesson  # type: ignore
from ..tools.get_client_statistics import tool_get_client_statistics  # type: ignore


MCP_PORT_ALENA = os.getenv("MCP_PORT_ALENA")  # 5020
CHANNEL_IDS_ALENA = [item.strip() for item in os.getenv("CHANNEL_IDS_ALENA").split(",")]  # 20

mcp_alena = FastMCP(name="Alena")

mcp_alena.mount(tool_faq, "zena")
mcp_alena.mount(tool_get_client_lessons, "zena")
mcp_alena.mount(tool_update_client_info, "zena")
mcp_alena.mount(tool_remember_lesson_id, "zena")
mcp_alena.mount(tool_update_client_lesson, "zena")
mcp_alena.mount(tool_get_client_statistics, "zena")


if __name__ == "__main__":
    mcp_alena.run(transport="sse", port=MCP_PORT_ALENA, host="0.0.0.0")

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.server.server_sse_sofia

# ss -tulnp | grep :4002
# sudo fuser -k 4001/tcp
# sudo kill -9 1287533
