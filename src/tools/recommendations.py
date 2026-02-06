"""MCP-сервер поиска рекомендаций для услуг после записи в векторной базе."""

from typing import Any

from fastmcp import FastMCP

from ..qdrant.retriever_faq_services import (
    qdrant_collection_services,  # type: ignore
    retriever_hybrid_async,  # type: ignore
)


QDRANT_COLLECTION_SERVICES = qdrant_collection_services()

tool_recommendations = FastMCP(name="recommendations")


@tool_recommendations.tool(
    name="recommendations",
    description=(
        "Получение рекомендации по услуге.\n\n"
        "**Назначение:**\n"
        "Позволяет узнать рекомендации к посещению.\n\n"
        "**Args:**\n"
        "- session_id(str): id dialog session. **Обязательный параметр.**\n"
        "- product_name (str, required ): Название выбранной услуги.\n"
        "- channel_id (str, required ): id channal company.\n"
        "**Returns:**\n"
        "- list[dict]: services_name, description, recommendations.\n"
    ),
)
async def recommendations(
    session_id: str,
    product_name: str,
    channel_id: int,
) -> list[dict[str, Any]]:
    """Получать рекомендации по выбранной услуге через поиск в services."""
    _ = session_id  # если реально не используешь
    try:
        results = await retriever_hybrid_async(
            query=product_name,
            channel_id=channel_id,
            database_name=QDRANT_COLLECTION_SERVICES,
            limit=1,
        )
    except Exception:
        return []

    allowed_keys = ["services_name", "description", "pre_session_instructions"]
    return [{k: s[k] for k in allowed_keys if k in s} for s in results] or []
