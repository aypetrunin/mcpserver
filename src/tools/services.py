"""MCP-сервер поиска информации по типам услуг в векторной базе."""

from typing import Any

from fastmcp import FastMCP

from ..qdrant.retriever_faq_services import (
    qdrant_collection_services,  # type: ignore
    retriever_hybrid_async,  # type: ignore
)


QDRANT_COLLECTION_SERVICES = qdrant_collection_services()

tool_services = FastMCP(name="services")


@tool_services.tool(
    name="services",
    description=(
        "Получение полной информации об услуге, показаниям и противопоказаниям к услуге и как подготовится к услуге по текстовому запросу пользователя.\n\n"
        "**Назначение:**\n"
        "Используется для поиска информации о конкретной медицинской услуге или категории услуг, которую выбрал клиент.\n"
        "Позволяет узнать подробности: описание услуги, показания, противопоказания и подготовку к посещению.\n\n"
        "**Примеры запросов:**\n"
        '- "Расскажите подробнее о диагностике позвоночника"\n'
        "- \"Что входит в услугу 'Check-up для женщин'?\"\n"
        '- "Какие противопоказания у процедуры МРТ?"\n'
        '- "Что нужно взять с собой на гастроскопию?"\n'
        '- "Что представляет собой процедура ...\n'
        '- "В чём различие процедур ...\n'
        '- "Как проводится процедура ...\n'
        '- "Что такое прессотерапия, LPG-массаж, Сфера-массаж ... \n'
        '- "Расскажите подробнее о процедуре ...\n'
        '- "В чем преимущества процедуры ...?\n'
        '- "Какая услуга лучше подходит для ...?\n'
        '- "Что входит в состав процедуры ...?\n'
        '- "Чем услуги ... отличаются друг от друга?\n'
        '- "Какие этапы включает процедура ...?\n'
        '- "Для чего нужна услуга ...?\n'
        '- "С какими показаниями рекомендуется процедура ...?\n'
        '- "Можете сравнить процедуры ... и ...?\n'
        '- "Какой эффект дает процедура ...?\n'
        '- "Почему стоит выбрать именно ...?\n'
        '- "Чем отличается ... от ...?\n'
        '- "По каким критериям выбирать между ... и ...?\n'
        '- "Можно ли совместить процедуры ... и ...?\n'
        '- "Какой результат ожидать от процедуры ...?\n'
        '- "Подходит ли ... для моего случая?\n'
        '- "Какая процедура эффективнее при ...?\n'
        '- "Что особенного в услуге ...?\n'
        '- "Сколько длится процедура ... и как она выполняется?\n'
        '- "Какие ощущения во время/после услуги ...?\n'
        '- "В чем плюс комплекса ...?\n\n'
        "**Args:**\n"
        "- query (str, required ): A natural language query describing the medical service or category of interest. "
        "- channel_id (str, required ): id channal company. \n"
        "Examples: 'Tell me about spine diagnostics', 'What is included in MRI?', "
        "'Contraindications for endoscopy', 'Preparation for ultrasound exam'.\n\n"
        "**Returns:**\n"
        "- list[dict]: A list of relevant services with structured details including description, indications, "
        "contraindications, and pre-session instructions."
    ),
)
async def services(
    query: str,
    channel_id: str,
) -> list[dict[str, Any]]:
    """Функция поиска информации по типам услуг."""
    return await retriever_hybrid_async(
        query=query, channel_id=int(channel_id), database_name=QDRANT_COLLECTION_SERVICES
    )
