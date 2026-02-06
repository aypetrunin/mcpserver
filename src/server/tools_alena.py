"""
tenant_alena.py — сборка списка tools для tenant'а Алёна (alena).

ВАЖНО:
- Никаких чтений env, print, создания клиентов на уровне модуля.
- Всё делаем внутри функций (factory-подход).
- Namespace ("zena") здесь не используется: он задаётся централизованно в server_registry.py.
"""

from typing import Any

from ..tools.faq import tool_faq  # type: ignore
from ..tools.lesson_id import tool_remember_lesson_id  # type: ignore
from ..tools.get_client_lessons import tool_get_client_lessons  # type: ignore
from ..tools.update_client_info import tool_update_client_info  # type: ignore
from ..tools.update_client_lesson import tool_update_client_lesson  # type: ignore
from ..tools.get_client_statistics import tool_get_client_statistics  # type: ignore

Tool = Any


async def build_tools_alena(server_name: str, channel_ids: list[str]) -> list[Tool]:
    """
    Собираем список tools для Алёна.

    channel_ids сейчас не используются, но оставлены для единого интерфейса
    (все tenant builders имеют одинаковую сигнатуру).
    server_name тоже не используется.
    """
    _ = server_name
    _ = channel_ids

    return [
        tool_faq,
        tool_get_client_lessons,
        tool_update_client_info,
        tool_remember_lesson_id,
        tool_update_client_lesson,
        tool_get_client_statistics,
    ]
