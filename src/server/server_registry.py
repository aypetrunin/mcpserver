"""
server_registry.py — реестр (список) MCP-tenant'ов, которые мы запускаем.

Идея:
- описываем каждого tenant'а объектом ServerSpec
- main_v2.py импортирует SERVERS и запускает их
- tools_namespace ("zena") задаётся здесь один раз, без копипасты по tenant-файлам

ВАЖНО:
- никаких defaults: все порты/каналы должны приходить из env (dev.env/prod.env или Docker env)
"""

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from fastmcp import FastMCP

Tool = Any
BuildToolsFn = Callable[[str, list[str]], Awaitable[list[Tool]]]
BuildMcpFn = Callable[[], Awaitable[FastMCP]]


@dataclass(frozen=False)
class ServerSpec:
    """
    name            — имя tenant'а (для логов)
    env_port        — env переменная с портом
    channel_ids_env — env переменная со списком каналов
    build_tools     — async функция сборки списка tools (без namespace/mounts)
    tools_namespace — общий namespace инструментов для LangGraph CLI ("zena")
    build           — async функция сборки FastMCP (заполняется автоматически)
    """
    name: str
    env_port: str
    channel_ids_env: str
    build_tools: BuildToolsFn
    tools_namespace: str = "zena"

    build: BuildMcpFn | None = field(default=None, repr=False)


# ------------------------------------------------------------------
# tenant tool-builders
# ------------------------------------------------------------------
from .tools_sofia import build_tools_sofia
from .tools_anisa import build_tools_anisa
from .tools_alena import build_tools_alena
from .tools_annitta import build_tools_annitta
from .tools_anastasia import build_tools_anastasia
from .tools_valentina import build_tools_valentina
from .tools_marina import build_tools_marina
 

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
]

# ------------------------------------------------------------------
# Проставляем spec.build, чтобы main_v2.py мог оставаться прежним
# ------------------------------------------------------------------
from src.server.server_spec_factory import build_mcp_from_spec

for spec in SERVERS:
    spec.build = (lambda s=spec: build_mcp_from_spec(s))





# """
# server_registry.py — реестр (список) MCP-tenant'ов, которые мы запускаем.

# Зачем нужен реестр:
# - чтобы main_v2.py был "чистым": только запуск/остановка, без списка "кто запускается"
# - чтобы добавление нового tenant'а было в одном месте
# - чтобы избежать копипасты и путаницы

# Идея:
# - мы описываем каждого tenant'а объектом ServerSpec
# - main_v2.py просто импортирует список SERVERS
# """

# from dataclasses import dataclass
# from typing import Callable, Awaitable

# from fastmcp import FastMCP

# # --------------------------------------------------------------------------
# # Тип factory-функции, которая "собирает" MCP-сервер.
# # Важно: build() НЕ запускает сервер, а только создаёт объект FastMCP.
# # --------------------------------------------------------------------------
# BuildFn = Callable[[], Awaitable[FastMCP]]


# @dataclass(frozen=True)
# class ServerSpec:
#     """
#     Описание одного MCP-сервера (tenant).

#     name     — имя tenant'а (для логов)
#     env_port — имя переменной окружения, где лежит порт (например MCP_PORT_ALISA)
#     build    — функция, которая создаёт FastMCP (но не запускает)
#     """
#     name: str
#     env_port: str
#     build: BuildFn


# # --------------------------------------------------------------------------
# # Импортируем build_* функции для каждого tenant'а.
# # ВАЖНО: эти модули должны только СОБИРАТЬ сервер и не делать "побочных эффектов"
# # при импорте (не читать env на уровне модуля, не подключаться к БД и т.д.)
# # --------------------------------------------------------------------------
# from src.server.server_sse_sofia_v2 import build_mcp_sofia
# from src.server.server_sse_anisa_v2 import build_mcp_anisa
# from src.server.server_sse_alena_v2 import build_mcp_alena
# from src.server.server_sse_annitta_v2 import build_mcp_annitta
# from src.server.server_sse_anastasia_v2 import build_mcp_anastasia
# from src.server.server_sse_valentina_v2 import build_mcp_valentina
# from src.server.server_sse_marina_v2 import build_mcp_marina


# # --------------------------------------------------------------------------
# # Список ВСЕХ MCP-серверов, которые будут запущены.
# #
# # Добавить нового tenant'а:
# # 1) создать server_sse_<name>_v2.py с build_mcp_<name>()
# # 2) добавить импорт build_mcp_<name> выше
# # 3) добавить строку ServerSpec(...) в список ниже
# # --------------------------------------------------------------------------
# SERVERS: list[ServerSpec] = [
#     ServerSpec("sofia", "MCP_PORT_SOFIA", build_mcp_sofia),
#     ServerSpec("anisa", "MCP_PORT_ANISA", build_mcp_anisa),
#     ServerSpec("alena", "MCP_PORT_ALENA", build_mcp_alena),
#     ServerSpec("annitta", "MCP_PORT_ANNITTA", build_mcp_annitta),
#     ServerSpec("anastasia", "MCP_PORT_ANASTASIA", build_mcp_anastasia),
#     ServerSpec("valentina", "MCP_PORT_VALENTINA", build_mcp_valentina),
#     ServerSpec("marina", "MCP_PORT_MARINA", build_mcp_marina),
# ]
