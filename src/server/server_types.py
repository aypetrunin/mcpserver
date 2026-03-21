"""Типы и спецификации для MCP-серверов.

Модуль содержит общие типы и dataclass-описание MCP-tenant'а,
используемые при сборке и запуске FastMCP серверов.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from fastmcp import FastMCP


Tool = Any
BuildToolsFn = Callable[[str, list[str]], Awaitable[list[Tool]]]
BuildMcpFn = Callable[[], Awaitable[FastMCP]]


@dataclass
class ServerSpec:
    """Спецификация MCP-tenant'а.

    Описывает параметры запуска отдельного MCP-сервера:
    - имя tenant'а
    - env-переменные с портом и каналами
    - функции сборки tools и FastMCP
    """

    name: str
    env_port: str
    channel_ids_env: str
    build_tools: BuildToolsFn
    tools_namespace: str = "zena"
    build: BuildMcpFn | None = field(default=None, repr=False)
