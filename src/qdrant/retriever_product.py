"""
Модуль функции ретривера поиска услуг по zena2_products_services_view.

Цели рефакторинга (минимальные изменения поведения):
- НЕ читаем env на уровне модуля.
- Коллекцию берём из get_settings() лениво (после init_runtime()).
- Нормализуем Qdrant response -> points (единая обработка).
- Чиним формирование price.
- Чуть лучше типизация и поддерживаемость.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable

from qdrant_client import models
from qdrant_client.models import FieldCondition, PointStruct, ScoredPoint

from src.settings import get_settings
from .retriever_common import (
    ada_embeddings,
    get_bm25_model,
    get_qdrant_client,
    retry_request,
)

logger = logging.getLogger(__name__)

# -------------------- Константы --------------------
DEFAULT_LIMIT = 5
HYBRID_LIMIT = 12
FORMULA_LIMIT = 10


# -------------------- Настройки (лениво) --------------------
def collection_name() -> str:
    """Имя коллекции берём из Settings (кешируется), а не из os.getenv() на импорте."""
    return get_settings().QDRANT_COLLECTION_PRODUCTS


# -------------------- Вспомогательное: нормализация response -> points --------------------
def _extract_points(obj: Any) -> list[ScoredPoint | PointStruct]:
    """
    Возвращает список points из:
    - результата query_points (имеет .points)
    - результата scroll (у вас это уже list[PointStruct])
    - или если уже передан список points.
    """
    if obj is None:
        return []
    if hasattr(obj, "points"):
        pts = getattr(obj, "points", None)
        return list(pts) if pts else []
    if isinstance(obj, list):
        return obj
    # На всякий случай: если прилетел итератор
    if isinstance(obj, Iterable):
        return list(obj)
    return []


# -------------------- Вспомогательное: формат цены --------------------
def _format_price(price_min: Any, price_max: Any) -> str | None:
    """
    Нормализует представление цены.

    - min и max заданы и равны -> "X руб."
    - min и max заданы и разные -> "min - max руб."
    - задан только min -> "от min руб."
    - задан только max -> "до max руб."
    """
    if price_min is not None and price_max is not None:
        return f"{price_min} руб." if price_min == price_max else f"{price_min} - {price_max} руб."
    if price_min is not None:
        return f"от {price_min} руб."
    if price_max is not None:
        return f"до {price_max} руб."
    return None


# -------------------- Преобразование точек --------------------
def points_to_list(obj: Any) -> list[dict[str, Any]]:
    """Преобразует results Qdrant (response или points) в список словарей продукта."""
    points = _extract_points(obj)

    result: list[dict[str, Any]] = []
    for p in points:
        pl = getattr(p, "payload", None)
        if not pl:
            continue

        price_min = pl.get("price_min")
        price_max = pl.get("price_max")

        result.append(
            {
                "product_id": pl.get("product_id"),
                "product_name": pl.get("product_name"),
                "duration": pl.get("duration"),
                "price": _format_price(price_min, price_max),
            }
        )
    return result


# -------------------- Универсальный сборщик фильтров --------------------
def make_filter(
    channel_id: int | None = None,
    indications: list[str] | None = None,
    contraindications: list[str] | None = None,
    body_parts: list[str] | None = None,
    product_type: list[str] | None = None,
    use_should: bool = False,
) -> models.Filter | None:
    """Формирует объект фильтра Qdrant для запросов."""
    must: list[models.Condition] = []
    must_not: list[models.Condition] = []
    should: list[models.Condition] = []

    # --- Фильтрация по каналу ---
    if channel_id is not None:
        must.append(
            models.FieldCondition(
                key="channel_id",
                match=models.MatchValue(value=int(channel_id)),
            )
        )

    # --- Показания ---
    if indications:
        target = should if use_should else must
        target.extend(
            [
                models.FieldCondition(key="indications_key", match=models.MatchText(text=i))
                for i in indications
            ]
        )

    # --- Части тела ---
    if body_parts:
        must.extend(
            [models.FieldCondition(key="body_parts", match=models.MatchText(text=b)) for b in body_parts]
        )

    # --- Тип продукта ---
    if product_type:
        must.extend(
            [models.FieldCondition(key="product_type", match=models.MatchText(text=t)) for t in product_type]
        )

    # --- Противопоказания (исключение) ---
    if contraindications:
        must_not.extend(
            [
                models.FieldCondition(key="contraindications_key", match=models.MatchText(text=c))
                for c in contraindications
            ]
        )

    if any([must, must_not, should]):
        # Qdrant допускает None для секций фильтра — это ок
        return models.Filter(
            must=must or None,       # type: ignore[arg-type]
            must_not=must_not or None,  # type: ignore[arg-type]
            should=should or None,   # type: ignore[arg-type]
        )
    return None


# -------------------- Базовый поиск (только Ada embeddings) --------------------
async def retriever_product_async(
    query: str | None = None,
    indications: list[str] | None = None,
    contraindications: list[str] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Поиск продуктов по текстовому запросу и фильтрам."""
    query_filter = make_filter(indications=indications, contraindications=contraindications)
    col = collection_name()

    async def _logic() -> list[dict[str, Any]]:
        if query:
            query_vector = (await ada_embeddings([query]))[0]
            res = await get_qdrant_client().query_points(
                collection_name=col,
                query=query_vector,
                using="ada-embedding",
                with_payload=True,
                limit=limit,
                query_filter=query_filter,
            )
            return points_to_list(res)

        res, _ = await get_qdrant_client().scroll(
            collection_name=col,
            scroll_filter=query_filter,
            with_payload=True,
            limit=limit,
        )
        return points_to_list(res)

    return await retry_request(_logic)


# -------------------- Гибридный поиск (Ada + BM25, RRF fusion) --------------------
async def retriever_product_hybrid_async(
    channel_id: int,
    query: str | None = None,
    indications: list[str] | None = None,
    contraindications: list[str] | None = None,
    body_parts: list[str] | None = None,
    product_type: list[str] | None = None,
    limit: int = HYBRID_LIMIT,
) -> list[dict[str, Any]]:
    """Гибридный поиск (Ada + BM25) с Reciprocal Rank Fusion (RRF)."""
    query_filter = make_filter(
        channel_id=channel_id,
        indications=indications,
        contraindications=contraindications,
        body_parts=body_parts,
        product_type=product_type,
        use_should=True,
    )
    col = collection_name()

    logger.debug(
        "retriever_product_hybrid_async channel_id=%s query=%s limit=%s filter=%s",
        channel_id,
        (query[:80] + "...") if query and len(query) > 80 else query,
        limit,
        query_filter,
    )

    async def _logic() -> list[dict[str, Any]]:
        if query:
            qv_ada = (await ada_embeddings([query]))[0]
            qv_bm25 = next(get_bm25_model().query_embed(query))

            prefetch = [
                models.Prefetch(query=qv_ada, using="ada-embedding", limit=limit),
                models.Prefetch(
                    query=models.SparseVector(**qv_bm25.as_object()),
                    using="bm25",
                    limit=limit,
                ),
            ]

            res = await get_qdrant_client().query_points(
                collection_name=col,
                prefetch=prefetch,
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                with_payload=True,
                query_filter=query_filter,
                limit=limit,
            )
            return points_to_list(res)

        res, _ = await get_qdrant_client().scroll(
            collection_name=col,
            scroll_filter=query_filter,
            with_payload=True,
            limit=limit,
        )
        return points_to_list(res)

    return await retry_request(_logic)


# -------------------- Гибридный поиск с FormulaQuery --------------------
async def retriever_product_hybrid_mult_async(
    channel_id: int,
    query: str | None = None,
    indications: list[str] | None = None,
    contraindications: list[str] | None = None,
    body_parts: list[str] | None = None,
    product_type: list[str] | None = None,
    limit: int = FORMULA_LIMIT,
) -> list[dict[str, Any]]:
    """Расширенный гибридный поиск с FormulaQuery (веса/бустинг)."""
    query_filter = make_filter(
        channel_id=channel_id,
        indications=indications,
        contraindications=contraindications,
        body_parts=body_parts,
        product_type=product_type,
    )
    col = collection_name()

    async def _logic() -> list[dict[str, Any]]:
        if query:
            qv_ada = (await ada_embeddings([query]))[0]
            qv_bm25 = next(get_bm25_model().query_embed(query))

            prefetch = [
                models.Prefetch(query=qv_ada, using="ada-embedding", limit=limit),
                models.Prefetch(
                    query=models.SparseVector(**qv_bm25.as_object()),
                    using="bm25",
                    limit=limit,
                ),
            ]

            # NB: Формула зависит от версии qdrant-client. Если у вас это уже работает — ок.
            formula = models.FormulaQuery(
                formula=models.SumExpression(
                    sum=[
                        "$score",
                        models.MultExpression(
                            mult=[
                                0.3,
                                models.FieldCondition(
                                    key="mult_score_boosting",
                                    match=models.MatchAny(any=["mult_1"]),
                                ),
                            ]
                        ),
                        models.MultExpression(
                            mult=[
                                0.2,
                                models.FieldCondition(
                                    key="mult_score_boosting",
                                    match=models.MatchAny(any=["mult_2"]),
                                ),
                            ]
                        ),
                    ]
                )
            )

            res = await get_qdrant_client().query_points(
                collection_name=col,
                prefetch=prefetch,
                query=formula,
                with_payload=True,
                query_filter=query_filter,
                limit=limit,
            )
            return points_to_list(res)

        res, _ = await get_qdrant_client().scroll(
            collection_name=col,
            scroll_filter=query_filter,
            with_payload=True,
            limit=limit,
        )
        return points_to_list(res)

    return await retry_request(_logic)


# -------------------- Тестовый запуск --------------------
if __name__ == "__main__":
    from src.runtime import init_runtime
    from main_v2 import setup_logging

    init_runtime()  # ← КЛЮЧЕВО
    setup_logging()

    async def main() -> None:
        results = await retriever_product_hybrid_async(
            channel_id=2,
            query='массаж',
            # indications=["отечность"],
            # body_parts=["лицо"],
        )
        logger.info("Результаты: %s элементов", len(results))

    asyncio.run(main())

# # cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.qdrant.retriever_product



# """Модуль функции ретривера поиска услуг по zena2_products_services_view."""

# import logging
# import asyncio
# import os
# from typing import Any, Dict, List, Union

# from qdrant_client.models import ScoredPoint, PointStruct
# from qdrant_client import models
# from qdrant_client.models import FieldCondition

# from .retriever_common import (
#     ada_embeddings,  # Функция генерации dense-векторов OpenAI (Ada)
#     get_bm25_model,  # Sparse-векторная модель BM25 (fastembed)
#     get_qdrant_client,  # Асинхронный клиент Qdrant
#     retry_request,  # Надёжный вызов с повторными попытками
# )

# logger = logging.getLogger(__name__)

# # -------------------- Конфигурация --------------------
# COLLECTION_NAME = os.getenv(
#     "QDRANT_COLLECTION_PRODUCTS", "zena2_products_services_view"
# )


# # -------------------- Преобразование точек --------------------
# def points_to_list(points: Union[List[ScoredPoint], List[PointStruct]]) -> list[dict[str, Any]]:
#     """Преобразует результаты запроса Qdrant в список словарей продукта.

#     Аргументы:
#         points: (Union[ScoredPoint, Record]): Результат запроса Qdrant.

#     Возвращает:
#         list[dict]: Список словарей, содержащих поля продукта: имя, тип, длительность, цена и т.д.
#     """
#     # Если пришёл объект с полем .points — извлекаем его
#     if hasattr(points, "points"):
#         points = points.points

#     result = []
#     for p in points:
#         pl = p.payload  # payload — это словарь, сохранённый в точке Qdrant
#         if not pl:  # ← Проверка на None/пустой payload
#             continue

#         price_min = pl.get("price_min")
#         price_max = pl.get("price_max")

#         # Формируем карточку продукта
#         result.append({
#             "product_id": pl.get("product_id"),
#             "product_name": pl.get("product_name"),
#             "duration": pl.get("duration"),
#             "price": (
#                 f"{price_min} руб."
#                 if price_min == price_max
#                 else f"{price_min} - {price_max} руб."
#             ) if price_min is not None and price_max is not None and price_min == price_max else None,
#         })
#     return result


# # -------------------- Универсальный сборщик фильтров --------------------
# def make_filter(
#     channel_id: int | None = None,
#     indications: List[str] | None = None,
#     contraindications: List[str] | None = None,
#     body_parts: List[str] | None = None,
#     product_type: List[str] | None = None,
#     use_should: bool = False,
# ) -> models.Filter | None:
#     """Формирует объект фильтра Qdrant для запросов.

#     Аргументы:
#         channel_id: фильтр по ID канала
#         indications: список показаний
#         contraindications: список противопоказаний
#         body_parts: список частей тела
#         product_type: тип продукта (например, "разовый", "абонемент")
#         use_should: если True, используется мягкое соответствие (should), а не строгое (must)

#     Возвращает:
#         models.Filter или None, если фильтры не заданы
#     """
#     # В функции make_filter:
#     must: list[FieldCondition] = []
#     must_not: list[FieldCondition] = []
#     should: list[FieldCondition] = [] 

#     # --- Фильтрация по каналу ---
#     if channel_id:
#         must.append(
#             models.FieldCondition(
#                 key="channel_id", match=models.MatchValue(value=int(channel_id))
#             )
#         )

#     # --- Фильтрация по показаниям ---
#     if indications:
#         (should if use_should else must).extend(
#             [
#                 models.FieldCondition(
#                     key="indications_key", match=models.MatchText(text=i)
#                 )
#                 for i in indications
#             ]
#         )

#     # --- Фильтрация по частям тела ---
#     if body_parts:
#         must.extend(
#             [
#                 models.FieldCondition(key="body_parts", match=models.MatchText(text=b))
#                 for b in body_parts
#             ]
#         )

#     # --- Фильтрация по типу продукта ---
#     if product_type:
#         must.extend(
#             [
#                 models.FieldCondition(
#                     key="product_type", match=models.MatchText(text=t)
#                 )
#                 for t in product_type
#             ]
#         )

#     # --- Исключение по противопоказаниям ---
#     if contraindications:
#         must_not.extend(
#             [
#                 models.FieldCondition(
#                     key="contraindications_key", match=models.MatchText(text=c)
#                 )
#                 for c in contraindications
#             ]
#         )

#     # Возвращаем собранный фильтр, если есть условия
#     if any([must, must_not, should]):
#         return models.Filter(
#             must=must if must else None,  # type: ignore[arg-type]
#             must_not=must_not if must_not else None,  # type: ignore[arg-type]
#             should=should if should else None,  # type: ignore[arg-type]
#         )
#     return None


# # -------------------- Базовый поиск (только Ada embeddings) --------------------
# async def retriever_product_async(
#     query: str | None = None,
#     indications: list[str] | None = None,
#     contraindications: list[str] | None = None,
# ) -> list[dict[str, Any]]:
#     """Выполняет поиск продуктов по текстовому запросу и фильтрам по показаниям и противопоказаниям.

#     Аргументы:
#         query: поисковая строка (например, "массаж лица")
#         indications: фильтр по показаниям
#         contraindications: фильтр по противопоказаниям

#     Возвращает:
#         Список найденных продуктов с кратким описанием.
#     """
#     query_filter = make_filter(
#         indications=indications, contraindications=contraindications
#     )

#     async def _logic() -> list[dict[str, Any]]:
#         if query:
#             # Создаём dense-вектор OpenAI Ada
#             query_vector = (await ada_embeddings([query]))[0]

#             # Поиск ближайших точек в Qdrant
#             res = await get_qdrant_client().query_points(
#                 collection_name=COLLECTION_NAME,
#                 query=query_vector,
#                 using="ada-embedding",
#                 with_payload=True,
#                 limit=5,
#                 query_filter=query_filter,
#             )
#         else:
#             # Если запроса нет — просто скроллим коллекцию
#             res, _ = await get_qdrant_client().scroll(
#                 collection_name=COLLECTION_NAME,
#                 scroll_filter=query_filter,
#                 with_payload=True,
#                 limit=5,
#             )
#         return points_to_list(res)

#     # Оборачиваем вызов в retry для надёжности
#     return await retry_request(_logic)


# # -------------------- Гибридный поиск (Ada + BM25, RRF fusion) --------------------
# async def retriever_product_hybrid_async(
#     channel_id: int,
#     query: str | None = None,
#     indications: list[str] | None = None,
#     contraindications: list[str] | None = None,
#     body_parts: list[str] | None = None,
#     product_type: list[str] | None = None,
# ) -> list[dict[str, Any]]:
#     """Гибридный поиск.

#     Поиск объединяющий dense-векторы (OpenAI Ada)
#     и sparse-векторы (BM25) с помощью Reciprocal Rank Fusion (RRF).
#     Используется, если нужно объединить "понимание смысла" и "точное совпадение слов".

#     Аргументы:
#         channel_id: фильтр по каналу
#         query: поисковая строка
#         indications, contraindications, body_parts, product_type: дополнительные фильтры

#     Возвращает:
#         Список найденных продуктов с агрегированным рейтингом.
#     """
#     query_filter = make_filter(
#         channel_id=channel_id,
#         indications=indications,
#         contraindications=contraindications,
#         body_parts=body_parts,
#         product_type=product_type,
#         use_should=True,
#     )

#     logger.info(f"===retriever_product_hybrid_async===")
#     logger.info(f"query_filter: {query_filter}")

#     async def _logic() -> list[dict[str, Any]]:
#         if query:
#             # --- Генерация векторов ---
#             qv_ada = (await ada_embeddings([query]))[0]
#             qv_bm25 = next(get_bm25_model().query_embed(query))

#             # --- Настройка prefetch для гибридного поиска ---
#             prefetch = [
#                 models.Prefetch(query=qv_ada, using="ada-embedding", limit=12),
#                 models.Prefetch(
#                     query=models.SparseVector(**qv_bm25.as_object()),
#                     using="bm25",
#                     limit=12,
#                 ),
#             ]

#             # --- Выполнение гибридного поиска (RRF) ---
#             res = await get_qdrant_client().query_points(
#                 collection_name=COLLECTION_NAME,
#                 prefetch=prefetch,
#                 query=models.FusionQuery(fusion=models.Fusion.RRF),
#                 with_payload=True,
#                 query_filter=query_filter,
#                 limit=12,
#             )
#         else:
#             # --- Если текста нет — просто фильтрация по полям ---
#             res, _ = await get_qdrant_client().scroll(
#                 collection_name=COLLECTION_NAME,
#                 scroll_filter=query_filter,
#                 with_payload=True,
#                 limit=12,
#             )
#         return points_to_list(res)

#     return await retry_request(_logic)


# # -------------------- Гибридный поиск с FormulaQuery --------------------
# async def retriever_product_hybrid_mult_async(
#     channel_id: int,
#     query: str | None = None,
#     indications: list[str] | None = None,
#     contraindications: list[str] | None = None,
#     body_parts: list[str] | None = None,
#     product_type: list[str] | None = None,
# ) -> list[dict[str, Any]]:
#     """Расширенный гибридный поиск.

#     Поиск использующий FormulaQuery
#     для задания кастомных весов при объединении скоринговых факторов.
#     Подходит для бустинга релевантности по дополнительным полям.

#     Аргументы:
#         channel_id: ID канала
#         query: поисковая строка
#         indications, contraindications, body_parts, product_type: фильтры

#     Возвращает:
#         Список найденных продуктов с учётом пользовательских весов.
#     """
#     query_filter = make_filter(
#         channel_id=channel_id,
#         indications=indications,
#         contraindications=contraindications,
#         body_parts=body_parts,
#         product_type=product_type,
#     )

#     async def _logic() -> list[dict[str, Any]]:
#         if query:
#             qv_ada = (await ada_embeddings([query]))[0]
#             qv_bm25 = next(get_bm25_model().query_embed(query))

#             prefetch = [
#                 models.Prefetch(query=qv_ada, using="ada-embedding", limit=10),
#                 models.Prefetch(
#                     query=models.SparseVector(**qv_bm25.as_object()),
#                     using="bm25",
#                     limit=10,
#                 ),
#             ]

#             # --- FormulaQuery: объединение с весами ---
#             formula = models.FormulaQuery(
#                 formula=models.SumExpression(
#                     sum=[
#                         "$score",
#                         # Бустинг по мультипликативным признакам
#                         models.MultExpression(
#                             mult=[
#                                 0.3,
#                                 models.FieldCondition(
#                                     key="mult_score_boosting",
#                                     match=models.MatchAny(any=["mult_1"]),
#                                 ),
#                             ]
#                         ),
#                         models.MultExpression(
#                             mult=[
#                                 0.2,
#                                 models.FieldCondition(
#                                     key="mult_score_boosting",
#                                     match=models.MatchAny(any=["mult_2"]),
#                                 ),
#                             ]
#                         ),
#                     ]
#                 )
#             )

#             res = await get_qdrant_client().query_points(
#                 collection_name=COLLECTION_NAME,
#                 prefetch=prefetch,
#                 query=formula,
#                 with_payload=True,
#                 query_filter=query_filter,
#                 limit=10,
#             )
#         else:
#             res, _ = await get_qdrant_client().scroll(
#                 collection_name=COLLECTION_NAME,
#                 scroll_filter=query_filter,
#                 with_payload=True,
#                 limit=10,
#             )
#         return points_to_list(res)

#     return await retry_request(_logic)


# # -------------------- Тестовый запуск --------------------
# if __name__ == "__main__":

#     async def main() -> None:
#         """Пример тестового вызова гибридного поиска.

#         Ищет массажные услуги по фильтрам и запросу.
#         """

#         from src.runtime import init_runtime

#         init_runtime()  # ← КЛЮЧЕВО
#         results = await retriever_product_async(
#             # channel_id=1,
#             query="лпг массаж",
#             # indications=["отечность"],
#             # # contraindications=["высокое"],
#             # body_parts=["лицо"],
#             # product_type=["разовый"]
#         )
#         logger.info(f"Результаты: {len(results)} элементов")
#         for row in results:
#             pass
#             # print(row["body_parts"])
#             # print(row["indications_key"])
#             # print()
#             # logger.info(results[:3])

#     asyncio.run(main())


# # cd /home/copilot_superuser/petrunin/zena/mcpserver
# # uv run python -m src.qdrant.retriever_product
