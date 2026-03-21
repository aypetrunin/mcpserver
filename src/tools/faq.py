"""MCP-сервер для поиска ответов на FAQ.

Контракт:
- ok(list[dict]) — поиск выполнен корректно (список может быть пустым)
- err(code, error) — ошибка валидации или инфраструктуры
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok

from ..qdrant.collections import faq_collection
from ..qdrant.retriever_faq_services import retriever_hybrid_async  # type: ignore


logger = logging.getLogger(__name__)

tool_faq = FastMCP(name="faq")


@tool_faq.tool(
    name="faq",
    description=(
        "Ответ на часто задаваемые клиентами **организационные вопросы**.\n\n"
        "**Назначение:**\n"
        "Используется, когда клиент интересуется общими правилами, графиком, "
        "подробной информацией о персонале, политикой клуба и подобными вопросами.\n\n"
        "**Примеры вопросов:**\n"
        "- Условия заморозки абонемента\n"
        "- Возможна ли рассрочка?\n"
        "- Как отменить или перенести запись?\n"
        "- Какой у вас график работы?\n"
        "- Какая квалификация у мастера Ивановой?\n"
        "- Принимаете ли вы сертификаты или подарочные карты?\n\n"
        "**Args:**\n"
        "- `query` (`str`, required): Вопрос клиента в естественном языке.\n"
        "- `channel_id` (`str`, required): ID канала / филиала.\n\n"
        "**Returns:**\n"
        "- Payload[list[dict]] в едином формате\n"
    ),
)
async def faq(
    query: str,
    channel_id: str,
) -> Payload[list[dict[str, Any]]]:
    """
    Поиск ответа на часто задаваемые организационные вопросы клиентов.

    Выполняет валидацию входных параметров и обращается к FAQ-хранилищу
    для получения релевантных ответов.
    """
    # --- 1. Валидация входа ---
    if not query or not query.strip():
        return err(
            code="validation_error",
            error="Параметр query не должен быть пустым.",
        )

    try:
        channel_id_int = int(channel_id)
    except (TypeError, ValueError):
        return err(
            code="validation_error",
            error="Некорректный channel_id: ожидается числовое значение.",
        )

    logger.info("[faq] query=%r channel_id=%s", query, channel_id_int)

    # --- 2. Поиск ---
    try:
        result = await retriever_hybrid_async(
            query=query,
            channel_id=channel_id_int,
            database_name=faq_collection(),
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("[faq] search failed")
        return err(
            code="search_failed",
            error="Ошибка поиска ответа. Попробуйте позже.",
        )

    # --- 3. Нормальный исход ---
    if not isinstance(result, list):
        return err(
            code="invalid_response",
            error="Неверный формат ответа от поискового сервиса.",
        )

    return ok(result)
