"""MCP-сервер поиска информации по типам услуг в векторной базе.

Informational tool: retrieval-only.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from src.crm._crm_result import Payload, ok

from ..qdrant.collections import services_collection
from ..qdrant.retriever_faq_services import retriever_hybrid_async  # type: ignore


logger = logging.getLogger(__name__)

tool_services = FastMCP(name="services")


@tool_services.tool(
    name="services",
    description=(
        "Получение полной информации об услуге, показаниях, противопоказаниях "
        "и подготовке к услуге по текстовому запросу пользователя.\n\n"
        "**Назначение:**\n"
        "Используется для получения справочной информации о медицинских услугах.\n\n"
        "**Args:**\n"
        "- query (`str`, required): Вопрос пользователя об услуге.\n"
        "- channel_id (`str`, required): ID филиала.\n\n"
        "**Returns:**\n"
        "- Payload[list[dict]]: Список найденных услуг или пустой список.\n"
    ),
)
async def services(
    query: str,
    channel_id: str,
) -> Payload[list[dict[str, Any]]]:
    """Поиск информации по услугам (описание, показания, противопоказания)."""
    try:
        channel_id_int = int(channel_id)
    except (TypeError, ValueError):
        # Для informational tool — тихо возвращаем пусто
        logger.warning("[services] invalid channel_id=%r", channel_id)
        return ok([])

    try:
        results = await retriever_hybrid_async(
            query=query,
            channel_id=channel_id_int,
            database_name=services_collection(),
        )
        return ok(results)

    except asyncio.CancelledError:
        raise

    except Exception:
        logger.exception("[services] retrieval failed")
        # НЕ err — retrieval-инструменты не должны ломать диалог
        return ok([])
