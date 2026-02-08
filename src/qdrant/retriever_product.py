"""Модуль функции ретривера поиска услуг по zena2_products_services_view.

Цели рефакторинга (минимальные изменения поведения):
- НЕ читаем env/settings на уровне модуля.
- Имя коллекции берём через qdrant.collections (лениво, после init_runtime()).
- Нормализуем Qdrant response -> points (единая обработка).
- Чиним формирование price.
- Чуть лучше типизация и поддерживаемость.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
import logging
from typing import Any

from qdrant_client import models
from qdrant_client.models import PointStruct, ScoredPoint

from .collections import products_collection
from .retriever_common import (
    ada_embeddings,
    get_bm25_model,
    get_qdrant_client,
    retry_request,
)


logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 5
HYBRID_LIMIT = 12
FORMULA_LIMIT = 10


def _extract_points(obj: Any) -> list[ScoredPoint | PointStruct]:
    """Возвращает список points из разных форматов ответа.

    - результата query_points (имеет .points)
    - результата scroll (обычно list[PointStruct])
    - или если уже передан список/итерируемое points
    """
    if obj is None:
        return []
    if hasattr(obj, "points"):
        pts = getattr(obj, "points", None)
        return list(pts) if pts else []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, Iterable):
        return list(obj)
    return []


def _to_number_or_none(x: Any) -> int | float | None:
    """Пытается привести x к числу (int/float). Если нельзя — None."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return x
    # иногда прилетает строкой "1500" или "1500.0"
    if isinstance(x, str):
        s = x.strip().replace(",", ".")
        if not s:
            return None
        try:
            v = float(s)
            # чтобы "1500.0" не выглядело странно
            return int(v) if v.is_integer() else v
        except ValueError:
            return None
    return None


def _format_price(price_min: Any, price_max: Any) -> str | None:
    """Нормализует представление цены.

    - min и max заданы и равны -> "X руб."
    - min и max заданы и разные -> "min - max руб."
    - задан только min -> "от min руб."
    - задан только max -> "до max руб."
    """
    pmin = _to_number_or_none(price_min)
    pmax = _to_number_or_none(price_max)

    if pmin is not None and pmax is not None:
        if pmin == pmax:
            return f"{pmin} руб."
        return f"{pmin} - {pmax} руб."
    if pmin is not None:
        return f"от {pmin} руб."
    if pmax is not None:
        return f"до {pmax} руб."
    return None


def points_to_list(obj: Any) -> list[dict[str, Any]]:
    """Преобразует results Qdrant (response или points) в список словарей продукта."""
    points = _extract_points(obj)

    result: list[dict[str, Any]] = []
    for point in points:
        payload = getattr(point, "payload", None)
        if not isinstance(payload, dict) or not payload:
            continue

        result.append(
            {
                "product_id": payload.get("product_id"),
                "product_name": payload.get("product_name"),
                "duration": payload.get("duration"),
                "price": _format_price(
                    payload.get("price_min"), payload.get("price_max")
                ),
            }
        )
    return result


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

    if channel_id is not None:
        must.append(
            models.FieldCondition(
                key="channel_id",
                match=models.MatchValue(value=int(channel_id)),
            )
        )

    if indications:
        target = should if use_should else must
        target.extend(
            [
                models.FieldCondition(
                    key="indications_key",
                    match=models.MatchText(text=i),
                )
                for i in indications
            ]
        )

    if body_parts:
        must.extend(
            [
                models.FieldCondition(
                    key="body_parts",
                    match=models.MatchText(text=b),
                )
                for b in body_parts
            ]
        )

    if product_type:
        must.extend(
            [
                models.FieldCondition(
                    key="product_type",
                    match=models.MatchText(text=t),
                )
                for t in product_type
            ]
        )

    if contraindications:
        must_not.extend(
            [
                models.FieldCondition(
                    key="contraindications_key",
                    match=models.MatchText(text=c),
                )
                for c in contraindications
            ]
        )

    if any([must, must_not, should]):
        return models.Filter(
            must=must or None,
            must_not=must_not or None,
            should=should or None,
        )
    return None


def _sanitize_limit(limit: Any, default: int) -> int:
    """fail-fast: limit должен быть положительным int."""
    if isinstance(limit, int) and limit > 0:
        return limit
    return default


async def retriever_product_async(
    query: str | None = None,
    indications: list[str] | None = None,
    contraindications: list[str] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Поиск продуктов по текстовому запросу и фильтрам."""
    query_filter = make_filter(
        indications=indications,
        contraindications=contraindications,
    )
    col = products_collection()
    limit = _sanitize_limit(limit, DEFAULT_LIMIT)

    async def _logic() -> list[dict[str, Any]]:
        try:
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

        except asyncio.CancelledError:
            raise

    return await retry_request(_logic)


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
    col = products_collection()
    limit = _sanitize_limit(limit, HYBRID_LIMIT)

    logger.debug(
        "retriever_product_hybrid_async channel_id=%s query=%s limit=%s filter=%s",
        channel_id,
        (query[:80] + "...") if query and len(query) > 80 else query,
        limit,
        query_filter,
    )

    async def _logic() -> list[dict[str, Any]]:
        try:
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

        except asyncio.CancelledError:
            raise

    return await retry_request(_logic)


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
    col = products_collection()
    limit = _sanitize_limit(limit, FORMULA_LIMIT)

    async def _logic() -> list[dict[str, Any]]:
        try:
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

        except asyncio.CancelledError:
            raise

    return await retry_request(_logic)


if __name__ == "__main__":
    from main_v2 import setup_logging
    from src.runtime import init_runtime

    init_runtime()
    setup_logging()

    async def main() -> None:
        """Проверка."""
        results = await retriever_product_hybrid_async(
            channel_id=2,
            query="массаж",
        )
        logger.info("Результаты: %s элементов", len(results))

    asyncio.run(main())


# # cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.qdrant.retriever_product
