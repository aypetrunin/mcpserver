# src/timezone_utils.py
# ВАЖНО:
# Тайм-зона задаётся на уровне MCP-сервера (агента).
# Все филиалы, обслуживаемые данным сервером, находятся в одной тайм-зоне.
# office_id / channel_id НЕ используются для выбора TZ.


from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo


DEFAULT_TZ = "Europe/Moscow"


def get_tz_name(server_name: str) -> str:
    """
    Определяет IANA-таймзону для MCP-сервера.

    Таймзона берётся из переменной окружения вида:
    MCP_TZ_<ИМЯ_СЕРВЕРА>. Если переменная не задана,
    используется таймзона по умолчанию (DEFAULT_TZ).

    Args:
        server_name: Логическое имя MCP-сервера / агента
            (например: "sofia", "alisa").

    Returns:
        Строка с IANA-таймзоной
        (например: "Europe/Moscow", "Asia/Krasnoyarsk").
    """
    key = f"MCP_TZ_{server_name.upper()}"
    return (os.getenv(key) or DEFAULT_TZ).strip()


def get_tz(server_name: str) -> ZoneInfo:
    """
    Возвращает объект ZoneInfo для MCP-сервера.

    Используется для создания timezone-aware объектов datetime
    в локальной таймзоне конкретного агента.

    Args:
        server_name: Логическое имя MCP-сервера / агента.

    Returns:
        Объект ZoneInfo, соответствующий локальной таймзоне сервера.
    """
    return ZoneInfo(get_tz_name(server_name))


def now_local(server_name: str) -> datetime:
    """
    Возвращает текущее локальное время MCP-сервера.

    Возвращаемый datetime является timezone-aware и соответствует
    локальной таймзоне агента.

    Args:
        server_name: Логическое имя MCP-сервера / агента.

    Returns:
        Текущее локальное время в виде timezone-aware datetime.
    """
    return datetime.now(get_tz(server_name))


def parse_slot(
    server_name: str,
    slot: str,
    fmt_no_tz: str = "%Y-%m-%d %H:%M",
) -> datetime:
    """
    Парсит слот из CRM в timezone-aware datetime.

    Правило:
    - если строка слота содержит TZ/offset (например: '2026-02-05T14:30:00+07:00' или '...Z'),
      парсим как timezone-aware и НЕ меняем tzinfo.
    - если TZ/offset отсутствует (например: '2026-02-05 14:30'),
      считаем, что это локальное время агента, и "приклеиваем" его TZ.

    Возвращает timezone-aware datetime.
    """
    s = slot.strip()

    # 1) Попытка ISO8601 с timezone: 2026-02-05T14:30:00+07:00 / ...Z
    # datetime.fromisoformat не понимает 'Z', заменяем на '+00:00'
    try:
        iso = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is not None:
            return dt
    except ValueError:
        pass

    # 2) Формат без TZ (старый вариант) -> приклеиваем TZ агента
    dt_naive = datetime.strptime(s, fmt_no_tz)
    return dt_naive.replace(tzinfo=get_tz(server_name))
