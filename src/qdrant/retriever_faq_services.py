"""
Модуль функции ретривера векторных баз faq, services и временной для маппинга.

Важно:
- НЕ читаем env на уровне модуля.
- Коллекции берём из get_settings() лениво (после init_runtime()).
"""

import asyncio
import logging
from functools import lru_cache
from typing import Any

from qdrant_client import models

from src.settings import get_settings
from .retriever_common import (
    ada_embeddings,     # Функция генерации dense-векторов OpenAI (Ada)
    get_bm25_model,     # Sparse-векторная модель BM25 (fastembed)
    get_qdrant_client,  # Асинхронный клиент Qdrant
    retry_request,      # Обёртка для надёжного выполнения с повторными попытками
)

logger = logging.getLogger(__name__)


# ===============================================================
# 🔧 Ленивая конфигурация коллекций Qdrant (через Settings)
# ===============================================================
def qdrant_collection_faq() -> str:
    return get_settings().QDRANT_COLLECTION_FAQ


def qdrant_collection_services() -> str:
    return get_settings().QDRANT_COLLECTION_SERVICES


@lru_cache(maxsize=1)
def database_fields() -> dict[str, list[str]]:
    """
    Ленивая и кешируемая карта полей по коллекциям.

    Почему так:
    - get_settings() читает env один раз и кешируется
    - database_fields() строится после init_runtime(), когда env уже загружен
    - избегаем "захвата" дефолтов при импорте модуля
    """
    s = get_settings()
    return {
        s.QDRANT_COLLECTION_FAQ: [
            "question",
            "answer",
        ],
        s.QDRANT_COLLECTION_SERVICES: [
            "services_name",
            "body_parts",
            "description",
            "contraindications",
            "indications",
            "pre_session_instructions",
        ],
        "zena2_services_key": [  # Используется для маппинга products и services
            "id",
            "services_name",
        ],
    }


# ===============================================================
# 🔄 Преобразование точек (результатов Qdrant) в словари
# ===============================================================
async def points_to_dict(
    points: list[models.PointStruct],
    database_name: str,
) -> list[dict[str, Any]]:
    """Преобразует список объектов Qdrant в список словарей с данными из payload."""
    fields = database_fields().get(database_name, [])
    result: list[dict[str, Any]] = []

    for point in points:
        if point.payload is None:  # защита от None
            continue

        payload = {field: point.payload.get(field) for field in fields}
        payload["id"] = point.id
        result.append(payload)

    return result


# ===============================================================
# 🔍 Универсальный асинхронный поисковик с поддержкой гибридного режима
# ===============================================================
async def retriver_hybrid_async(
    query: str,
    database_name: str,
    channel_id: int | None = None,
    hybrid: bool = True,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Гибридный поиск в Qdrant (Ada + BM25 + RRF fusion) с retry."""

    async def _retriever_logic() -> list[dict[str, Any]]:
        # 1) Dense-вектор через OpenAI Ada
        query_vector = (await ada_embeddings([query]))[0]

        # 2) Sparse-вектор BM25, если включён гибрид
        query_bm25 = None
        if hybrid:
            query_bm25 = next(get_bm25_model().query_embed(query))

        # 3) Фильтр по channel_id (если задан)
        query_filter = None
        if channel_id is not None:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="channel_id",
                        match=models.MatchValue(value=channel_id),
                    )
                ]
            )

        # 4) Поиск в Qdrant
        if hybrid and query_bm25 is not None:
            prefetch = [
                models.Prefetch(query=query_vector, using="ada-embedding", limit=limit),
                models.Prefetch(
                    query=models.SparseVector(**query_bm25.as_object()),
                    using="bm25",
                    limit=limit,
                ),
            ]
            response = await get_qdrant_client().query_points(
                collection_name=database_name,
                prefetch=prefetch,
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                query_filter=query_filter,
                with_payload=True,
                limit=limit,
            )
        else:
            response = await get_qdrant_client().query_points(
                collection_name=database_name,
                query=query_vector,
                using="ada-embedding",
                query_filter=query_filter,
                with_payload=True,
                limit=limit,
            )

        # 5) Преобразование результатов
        return await points_to_dict(response.points, database_name)

    return await retry_request(_retriever_logic)


# ===============================================================
# 🧪 Тестовый запуск для проверки работы retriever
# ===============================================================
if __name__ == "__main__":

    async def main() -> None:
        # Поиск по базе FAQ
        results_faq = await retriver_hybrid_async(
            query="Абонент",
            database_name=qdrant_collection_faq(),
            channel_id=2,
        )
        logger.info("📘 FAQ results:")
        logger.info(results_faq)

        # Поиск по базе услуг
        results_services = await retriver_hybrid_async(
            query="Тейпирование",
            database_name=qdrant_collection_services(),
            channel_id=2,
        )
        logger.info("💆 Services results:")
        logger.info(results_services)

    asyncio.run(main())
