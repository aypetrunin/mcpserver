"""MCP-сервер поиска рекомендаций для услуг после записи в векторной базе.

Query-tool: выполняет поиск в Qdrant по названию услуги и возвращает рекомендации.
Контракт:
- ok(list[dict]) — поиск выполнен корректно (список может быть пустым)
- err(code,error) — ошибка валидации / инфраструктуры
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok

from ..qdrant.collections import services_collection
from ..qdrant.retriever_faq_services import retriever_hybrid_async  # type: ignore


logger = logging.getLogger(__name__)

tool_recommendations = FastMCP(name="recommendations")


@tool_recommendations.tool(
    name="recommendations",
    description=(
        "Получение рекомендации по услуге.\n\n"
        "**Назначение:**\n"
        "Позволяет узнать рекомендации к посещению.\n\n"
        "**Args:**\n"
        "- session_id (`str`, required): id dialog session.\n"
        "- product_name (`str`, required): Название выбранной услуги.\n"
        "- channel_id (`str`, required): id channel company.\n\n"
        "**Returns:**\n"
        "- Payload[list[dict]]: services_name, description, pre_session_instructions.\n"
    ),
)
async def recommendations(
    session_id: str,
    product_name: str,
    channel_id: str,
) -> Payload[list[dict[str, Any]]]:
    """Получать рекомендации по выбранной услуге через поиск в services."""
    _ = session_id  # если реально не используешь

    # ------------------------------------------------------------------
    # 1) Валидация входа (fail-fast)
    # ------------------------------------------------------------------
    if not isinstance(product_name, str) or not product_name.strip():
        return err(
            code="validation_error",
            error="Параметр product_name обязателен и не должен быть пустым.",
        )

    try:
        channel_id_int = int(channel_id)
    except (TypeError, ValueError):
        return err(
            code="validation_error",
            error="Некорректный channel_id: ожидается числовое значение.",
        )

    # ------------------------------------------------------------------
    # 2) Поиск в Qdrant
    # ------------------------------------------------------------------
    try:
        results = await retriever_hybrid_async(
            query=product_name,
            channel_id=channel_id_int,
            database_name=services_collection(),
            limit=1,
        )
    except asyncio.CancelledError:
        # cancel всегда пробрасываем (shutdown-safe)
        raise
    except Exception:
        logger.exception("[recommendations] search failed")
        return err(
            code="search_failed",
            error="Не удалось получить рекомендации. Попробуйте позже.",
        )

    # ------------------------------------------------------------------
    # 3) Нормализация ответа
    # ------------------------------------------------------------------
    allowed_keys = ("services_name", "description", "pre_session_instructions")

    if not isinstance(results, list):
        return err(
            code="invalid_response",
            error="Неверный формат ответа от поискового сервиса.",
        )

    filtered: list[dict[str, Any]] = []
    for s in results:
        if not isinstance(s, dict):
            continue
        filtered.append({k: s[k] for k in allowed_keys if k in s})

    return ok(filtered)
