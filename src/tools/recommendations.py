"""MCP-сервер поиска рекомендаций для услуг после записи в векторной базе."""

from typing import Any

from fastmcp import FastMCP

from ..qdrant.retriever_faq_services import retriver_hybrid_async  # type: ignore
from ..qdrant.retriever_faq_services import QDRANT_COLLECTION_SERVICES  # type: ignore



tool_recommendations = FastMCP(name="recommendations")

@tool_recommendations.tool(
    name="recommendations",
    description=(
        "Получение рекомендации по услуге.\n\n"
        "**Назначение:**\n"
        "Позволяет узнать рекомендации к посещению.\n\n"
        "**Args:**\n"
        "- session_id(str): id dialog session. **Обязательный параметр.**\n"
        "- product_name (str, required ): Название выбранной услуги."
        "- channel_id (str, required ): id channal company. \n"
        "**Returns:**\n"
        "- list[dict]: A list services_name, description, recommendations "
    ),
)
async def recommendations(
    session_id: str,
    product_name: str,
    channel_id: int,
) -> list[dict[str, Any]]:
    """Получение рекомендаций по выбранной услуге через поиск в таблице services."""
    try:
        results = await retriver_hybrid_async(
            query=product_name,
            channel_id=channel_id,
            database_name=QDRANT_COLLECTION_SERVICES,
            limit=1,
        )

        allowed_keys = ["services_name", "description", "pre_session_instructions", ]
        filtered_results = [{k: s[k] for k in allowed_keys if k in s} for s in results]
        
        return filtered_results or []  # ✅ Возвращаем пустой список при None
    
    except Exception as e:

        return []  # ✅ Безопасный fallback