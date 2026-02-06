"""Утилиты для работы с локальной тайм-зоной MCP-сервера."""

from __future__ import annotations

from datetime import datetime
import os
from zoneinfo import ZoneInfo


DEFAULT_TZ = "Europe/Moscow"
"""Тайм-зона по умолчанию."""


def get_tz_name(server_name: str) -> str:
    """Возвращает IANA-таймзону сервера."""
    key = f"MCP_TZ_{server_name.upper()}"
    return (os.getenv(key) or DEFAULT_TZ).strip()


def get_tz(server_name: str) -> ZoneInfo:
    """Возвращает ZoneInfo тайм-зоны сервера."""
    return ZoneInfo(get_tz_name(server_name))


def now_local(server_name: str) -> datetime:
    """Возвращает текущее локальное время сервера."""
    return datetime.now(get_tz(server_name))


def parse_slot(server_name: str, slot: str, fmt_no_tz: str = "%Y-%m-%d %H:%M") -> datetime:
    """Парсит слот CRM в timezone-aware datetime."""
    s = slot.strip()

    # ISO8601 с тайм-зоной / offset.
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        dt = None
    else:
        if dt.tzinfo is not None:
            return dt

    # Без тайм-зоны — считаем локальным временем сервера.
    dt_naive = datetime.strptime(s, fmt_no_tz)
    return dt_naive.replace(tzinfo=get_tz(server_name))
