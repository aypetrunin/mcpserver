"""Модуль ретривера для векторных баз FAQ / services.

Важно:
- НЕ читаем env/settings на уровне модуля.
- НЕ вызываем get_settings() вообще: имя коллекции и schema полей приходят снаружи.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from qdrant_client import models

from .collections import database_fields
from .retriever_common import (
    ada_embeddings,
    get_bm25_model,
    get_qdrant_client,
    retry_request,
)


logger = logging.getLogger(__name__)


def points_to_dict(
    points: list[models.PointStruct],
    database_name: str,
    *,
    include_none: bool = True,
) -> list[dict[str, Any]]:
    """
    Преобразует Qdrant points в список dict по whitelist-полям для конкретной коллекции.

    include_none:
      - True  -> ключи будут присутствовать даже если значение None
      - False -> None-поля не включаются (часто более LLM-friendly)
    """
    fields = database_fields().get(database_name, [])
    result: list[dict[str, Any]] = []

    for point in points:
        payload_src = point.payload if isinstance(point.payload, dict) else {}

        payload: dict[str, Any] = {}
        for field in fields:
            v = payload_src.get(field)
            if include_none:
                payload[field] = v
            else:
                if v is not None:
                    payload[field] = v

        # всегда включаем id (важно для downstream)
        payload["id"] = point.id
        result.append(payload)

    return result


async def retriever_hybrid_async(
    query: str,
    database_name: str,
    channel_id: int | None = None,
    hybrid: bool = True,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Гибридный поиск в Qdrant (Ada + BM25 + RRF fusion) с retry."""
    # fail-fast на дешёвых проверках
    if not isinstance(query, str) or not query.strip():
        return []
    if not isinstance(limit, int) or limit <= 0:
        return []

    async def _retriever_logic() -> list[dict[str, Any]]:
        try:
            client = get_qdrant_client()

            # embeddings
            query_vector = (await ada_embeddings([query]))[0]

            # bm25
            query_bm25 = None
            if hybrid:
                query_bm25 = next(get_bm25_model().query_embed(query))

            # filter
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

            # query
            if hybrid and query_bm25 is not None:
                prefetch = [
                    models.Prefetch(
                        query=query_vector, using="ada-embedding", limit=limit
                    ),
                    models.Prefetch(
                        query=models.SparseVector(**query_bm25.as_object()),
                        using="bm25",
                        limit=limit,
                    ),
                ]
                response = await client.query_points(
                    collection_name=database_name,
                    prefetch=prefetch,
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    query_filter=query_filter,
                    with_payload=True,
                    limit=limit,
                )
            else:
                response = await client.query_points(
                    collection_name=database_name,
                    query=query_vector,
                    using="ada-embedding",
                    query_filter=query_filter,
                    with_payload=True,
                    limit=limit,
                )

            return points_to_dict(response.points, database_name)

        except asyncio.CancelledError:
            # shutdown-safe
            raise

    # retry_request должен быть cancel-safe (CancelledError не ретраим)
    return await retry_request(_retriever_logic)
