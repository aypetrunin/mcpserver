from fastmcp import FastMCP
from typing import Optional

from ..qdrant.retriver_faq_services import retriver_hybrid_async, QDRANT_COLLECTION_SERVICES

tool_services = FastMCP(name="services")

@tool_services.tool(
    name="services",
    description=(
        "Получение полной информации об услуге, показаниям и противопоказаниям к услуге и как подготовится к услуге по текстовому запросу пользователя.\n\n"
        "**Назначение:**\n"
        "Используется для поиска информации о конкретной медицинской услуге или категории услуг, которую выбрал клиент.\n"
        "Позволяет узнать подробности: описание услуги, показания, противопоказания и подготовку к посещению.\n\n"
        "**Примеры запросов:**\n"
        "- \"Расскажите подробнее о диагностике позвоночника\"\n"
        "- \"Что входит в услугу 'Check-up для женщин'?\"\n"
        "- \"Какие противопоказания у процедуры МРТ?\"\n"
        "- \"Что нужно взять с собой на гастроскопию?\"\n\n"
        "**Args:**\n"
        "- query (str, required ): A natural language query describing the medical service or category of interest. "
        "- channel_id (str, required ): id channal company. \n"
        "Examples: 'Tell me about spine diagnostics', 'What is included in MRI?', "
        "'Contraindications for endoscopy', 'Preparation for ultrasound exam'.\n\n"
        "**Returns:**\n"
        "- list[dict]: A list of relevant services with structured details including description, indications, "
        "contraindications, and pre-session instructions."
    )
)
async def services(
    query: str,
    channel_id: int = None,
    ) -> list[dict]:
    return await retriver_hybrid_async(
        query=query,
        channel_id=channel_id,
        database_name=QDRANT_COLLECTION_SERVICES
    )
