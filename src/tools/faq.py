"""MCP-сервер для поиска ответов на FAQ."""

from typing import Any

from fastmcp import FastMCP

from ..qdrant.retriever_faq_services import (
    qdrant_collection_faq,  # type: ignore
    retriever_hybrid_async,  # type: ignore
)


QDRANT_COLLECTION_FAQ = qdrant_collection_faq()

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
        "- `list[dict]`: Список релевантных ответов из базы FAQ. Каждый элемент — словарь с полями:\n"
        "  - `id` (`int`): Уникальный идентификатор ответа\n"
        "  - `question` (`str`): Формулировка типового вопроса\n"
        "  - `answer` (`str`): Готовый ответ для отображения пользователю\n"
    ),
)
async def faq(
    query: str,
    channel_id: str,
) -> list[dict[str, Any]]:
    """Найти ответы на FAQ по запросу клиента."""
    return await retriever_hybrid_async(
        query=query,
        channel_id=int(channel_id),
        database_name=QDRANT_COLLECTION_FAQ,
    )
