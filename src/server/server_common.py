"""Утилиты для сборки и локального запуска FastMCP."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
import os
from pprint import pprint

from fastmcp import FastMCP


Mount = tuple[object, str]  # (tool, namespace)


def build_mcp(name: str, mounts: Iterable[Mount]) -> FastMCP:
    """Создаёт FastMCP и монтирует указанные инструменты в namespace."""
    mcp = FastMCP(name=name)
    for tool, namespace in mounts:
        mcp.mount(tool, namespace)
    return mcp


def require_env(name: str) -> str:
    """Возвращает значение обязательной переменной окружения или бросает ошибку."""
    val = os.getenv(name)
    if val is None or val.strip() == "":
        raise RuntimeError(f"Отсутствует необходимая переменная окружения: {name}")
    return val


def get_env_int(name: str) -> int:
    """Читает обязательную переменную окружения и парсит её как int."""
    raw = require_env(name)
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Некорректный {name}={raw!r}: ожидается целое число") from exc


def get_env_csv(name: str) -> list[str]:
    """Читает обязательную переменную окружения и парсит её как CSV-список."""
    raw = require_env(name)
    return [item.strip() for item in raw.split(",") if item.strip()]


def debug_print_tools(mcp: FastMCP) -> None:
    """Печатает список зарегистрированных tools (для локального дебага)."""
    tools = asyncio.run(mcp.get_tools())
    pprint(list(tools))
