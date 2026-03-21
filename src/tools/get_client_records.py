"""MCP-сервер для поиска текущих записей услуг клиента.

Контракт:
- ok(list) — CRM отработала без ошибок (список может быть пустым)
- err(code,error) — ошибка валидации / CRM / сети
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err

from ..crm.crm_get_client_records import get_client_records  # type: ignore


logger = logging.getLogger(__name__)

tool_records = FastMCP(name="records")


@tool_records.tool(
    name="records",
    description=(
        "Возвращает список услуг, на которые записан клиент.\n\n"
        "**Назначение:**\n"
        "Используется, когда клиент интересуется своими записями, "
        "чтобы увидеть расписание, перенести или отменить визит.\n\n"
        "**Примеры вопросов:**\n"
        "- Когда я записан?\n"
        "- На какое время я записан?\n"
        "- К кому я записан?\n"
        "- В каком офисе у меня запись?\n\n"
        "**Args:**\n"
        "- `user_companychat` (`str`, required): ID пользователя.\n"
        "- `channel_id` (`str`, required): ID филиала.\n\n"
        "**Returns (единый контракт):**\n"
        "- Payload[list[dict]]\n"
    ),
)
async def records(
    user_companychat: str,
    channel_id: str,
) -> Payload[list[dict[str, Any]]]:
    """Получить текущие записи клиента на услуги."""
    # ------------------------------------------------------------------
    # Что делаем: валидация входных аргументов tool-а.
    # ------------------------------------------------------------------
    # Раньше ValueError ловился общим except, но это:
    # - скрывает ошибки
    # - приводит к неединому формату ответа
    try:
        user_id_int = int(user_companychat)
        channel_id_int = int(channel_id)
    except (TypeError, ValueError):
        return err(
            code="validation_error",
            error="Некорректные параметры: user_companychat и channel_id должны быть числами.",
        )

    logger.info("[records] user=%s channel_id=%s", user_id_int, channel_id_int)

    # ------------------------------------------------------------------
    # Что делаем: просто возвращаем результат CRM-функции,
    # потому что она уже приведена к Payload (ok/err).
    # ------------------------------------------------------------------
    try:
        return await get_client_records(
            user_companychat=user_id_int,
            channel_id=channel_id_int,
        )
    except asyncio.CancelledError:
        # Что делаем: CancelledError не превращаем в err — важно для корректного shutdown.
        raise
    except Exception as exc:
        # Что делаем: защитный fallback на случай неожиданного бага в CRM-слое.
        logger.exception("[records] unexpected error: %s", exc)
        return err(
            code="internal_error", error="Не удалось получить записи. Попробуйте позже."
        )
