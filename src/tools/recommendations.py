"""MCP-сервер поиска рекомендаций для услуг после записи в векторной базе."""

from typing import Any

from fastmcp import FastMCP

from ..postgres.postgres_util import insert_dialog_state
from ..qdrant.retriever_faq_services import (
    QDRANT_COLLECTION_SERVICES,
    retriver_hybrid_async,
)

tool_recommendations = FastMCP(name="recommendations")

@tool_recommendations.tool(
    name="recommendations",
    description=(
        "Получение информации об услуге ПОСЛЕ ЗАПИСИ о противопоказаниям к услуге и как подготовится к услуге.\n\n"
        "**Назначение:**\n"
        "Используется для поиска информации о конкретной услуге выбрал клиент.\n"
        "Позволяет узнать подробности: описание услуги, противопоказания и подготовку к посещению.\n\n"
        "**Args:**\n"
        "- session_id(str): id dialog session. **Обязательный параметр.**\n"
        "- product_name (str, required ): Название выбранной услуги."
        "- channel_id (str, required ): id channal company. \n"
        "**Returns:**\n"
        "- list[dict]: A list of relevant services with structured details including description, indications, "
        "contraindications, and pre-session instructions."
    ),
)
async def recommendations(
    session_id: str,
    product_name: str,
    channel_id: int = None,
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
        
        insert_dialog_state(
            session_id=session_id,
            recommendations={"recommendations": results},
            name="new",
        )

        return filtered_results or []  # ✅ Возвращаем пустой список при None
    
    except Exception as e:

        return []  # ✅ Безопасный fallback