"""server_registry.py — реестр (список) MCP-tenant'ов, которые мы запускаем.

Идея:
- описываем каждого tenant'а объектом ServerSpec
- main_v2.py импортирует SERVERS и запускает их
- tools_namespace ("zena") задаётся здесь один раз, без копипасты по tenant-файлам

ВАЖНО:
- никаких defaults: все порты/каналы должны приходить из env (dev.env/prod.env или Docker env)
"""

from __future__ import annotations

from src.server.server_spec_factory import build_mcp_from_spec

from .server_types import BuildMcpFn, ServerSpec
from .tools_alena import build_tools_alena
from .tools_anastasia import build_tools_anastasia
from .tools_anisa import build_tools_anisa
from .tools_annitta import build_tools_annitta
from .tools_marina import build_tools_marina
from .tools_sofia import build_tools_sofia
from .tools_valentina import build_tools_valentina
from .tools_egoistka import build_tools_egoistka

SERVERS: list[ServerSpec] = [
    ServerSpec(
        name="sofia",
        env_port="MCP_PORT_SOFIA",
        channel_ids_env="CHANNEL_IDS_SOFIA",
        build_tools=build_tools_sofia,
    ),
    ServerSpec(
        name="anisa",
        env_port="MCP_PORT_ANISA",
        channel_ids_env="CHANNEL_IDS_ANISA",
        build_tools=build_tools_anisa,
    ),
    ServerSpec(
        name="alena",
        env_port="MCP_PORT_ALENA",
        channel_ids_env="CHANNEL_IDS_ALENA",
        build_tools=build_tools_alena,
    ),
    ServerSpec(
        name="annitta",
        env_port="MCP_PORT_ANNITTA",
        channel_ids_env="CHANNEL_IDS_ANNITTA",
        build_tools=build_tools_annitta,
    ),
    ServerSpec(
        name="anastasia",
        env_port="MCP_PORT_ANASTASIA",
        channel_ids_env="CHANNEL_IDS_ANASTASIA",
        build_tools=build_tools_anastasia,
    ),
    ServerSpec(
        name="valentina",
        env_port="MCP_PORT_VALENTINA",
        channel_ids_env="CHANNEL_IDS_VALENTINA",
        build_tools=build_tools_valentina,
    ),
    ServerSpec(
        name="marina",
        env_port="MCP_PORT_MARINA",
        channel_ids_env="CHANNEL_IDS_MARINA",
        build_tools=build_tools_marina,
    ),
    ServerSpec(
        name="egoistka",
        env_port="MCP_PORT_EGOISTKA",
        channel_ids_env="CHANNEL_IDS_EGOISTKA",
        build_tools=build_tools_egoistka,
    ),
]


def _build_for_spec(spec: ServerSpec) -> BuildMcpFn:
    """Возвращает фабрику build-функции для конкретного spec."""
    return lambda: build_mcp_from_spec(spec)


for spec in SERVERS:
    spec.build = _build_for_spec(spec)
