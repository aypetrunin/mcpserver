"""
server_registry.py — реестр (список) MCP-tenant'ов, которые мы запускаем.

Зачем нужен реестр:
- чтобы main_v2.py был "чистым": только запуск/остановка, без списка "кто запускается"
- чтобы добавление нового tenant'а было в одном месте
- чтобы избежать копипасты и путаницы

Идея:
- мы описываем каждого tenant'а объектом ServerSpec
- main_v2.py просто импортирует список SERVERS
"""

from dataclasses import dataclass
from typing import Callable, Awaitable

from fastmcp import FastMCP

# --------------------------------------------------------------------------
# Тип factory-функции, которая "собирает" MCP-сервер.
# Важно: build() НЕ запускает сервер, а только создаёт объект FastMCP.
# --------------------------------------------------------------------------
BuildFn = Callable[[], FastMCP | Awaitable[FastMCP]]


@dataclass(frozen=True)
class ServerSpec:
    """
    Описание одного MCP-сервера (tenant).

    name     — имя tenant'а (для логов)
    env_port — имя переменной окружения, где лежит порт (например MCP_PORT_ALISA)
    build    — функция, которая создаёт FastMCP (но не запускает)
    """
    name: str
    env_port: str
    build: BuildFn


# --------------------------------------------------------------------------
# Импортируем build_* функции для каждого tenant'а.
# ВАЖНО: эти модули должны только СОБИРАТЬ сервер и не делать "побочных эффектов"
# при импорте (не читать env на уровне модуля, не подключаться к БД и т.д.)
# --------------------------------------------------------------------------
from src.server.server_sse_alisa_v2 import build_mcp_alisa
from src.server.server_sse_sofia_v2 import build_mcp_sofia
from src.server.server_sse_anisa_v2 import build_mcp_anisa
from src.server.server_sse_alena_v2 import build_mcp_alena
from src.server.server_sse_annitta_v2 import build_mcp_annitta
from src.server.server_sse_anastasia_v2 import build_mcp_anastasia
from src.server.server_sse_valentina_v2 import build_mcp_valentina
from src.server.server_sse_marina_v2 import build_mcp_marina


# --------------------------------------------------------------------------
# Список ВСЕХ MCP-серверов, которые будут запущены.
#
# Добавить нового tenant'а:
# 1) создать server_sse_<name>_v2.py с build_mcp_<name>()
# 2) добавить импорт build_mcp_<name> выше
# 3) добавить строку ServerSpec(...) в список ниже
# --------------------------------------------------------------------------
SERVERS: list[ServerSpec] = [
    ServerSpec("alisa", "MCP_PORT_ALISA", build_mcp_alisa),
    ServerSpec("sofia", "MCP_PORT_SOFIA", build_mcp_sofia),
    ServerSpec("anisa", "MCP_PORT_ANISA", build_mcp_anisa),
    ServerSpec("alena", "MCP_PORT_ALENA", build_mcp_alena),
    ServerSpec("annitta", "MCP_PORT_ANNITTA", build_mcp_annitta),
    ServerSpec("anastasia", "MCP_PORT_ANASTASIA", build_mcp_anastasia),
    ServerSpec("valentina", "MCP_PORT_VALENTINA", build_mcp_valentina),
    ServerSpec("marina", "MCP_PORT_MARINA", build_mcp_marina),
]
