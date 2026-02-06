"""
Модуль сборки MCP-сервера для фирмы Алёна.

ВАЖНО:
- Никаких чтений env, print, создания клиентов на уровне модуля.
- Всё делаем внутри функций (factory-подход).
"""

from fastmcp import FastMCP

from .server_common import build_mcp, get_env_csv, run_standalone

from ..tools.faq import tool_faq  # type: ignore
from ..tools.lesson_id import tool_remember_lesson_id  # type: ignore
from ..tools.get_client_lessons import tool_get_client_lessons  # type: ignore
from ..tools.update_client_info import tool_update_client_info  # type: ignore
from ..tools.update_client_lesson import tool_update_client_lesson  # type: ignore
from ..tools.get_client_statistics import tool_get_client_statistics  # type: ignore


async def build_mcp_alena() -> FastMCP:
    """
    Собираем и возвращаем FastMCP сервер для Алёна.
    Ничего не запускаем тут, только создаём объект.
    """
    # channel_ids сейчас не используются,
    # но читаем их для единообразия конфигурации
    _ = get_env_csv("CHANNEL_IDS_ALENA")

    return build_mcp(
        name="Alena",
        mounts=[
            (tool_faq, "zena"),
            (tool_get_client_lessons, "zena"),
            (tool_update_client_info, "zena"),
            (tool_remember_lesson_id, "zena"),
            (tool_update_client_lesson, "zena"),
            (tool_get_client_statistics, "zena"),
        ],
    )


if __name__ == "__main__":
    run_standalone(
        build=build_mcp_alena,
        port_env="MCP_PORT_ALENA",
        defaults={
            "MCP_PORT_ALENA": "5099",
            "CHANNEL_IDS_ALENA": "20",
        },
        print_tools=True,
    )


# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run --active python -m src.server.server_sse_alena_v2
