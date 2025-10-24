import pytest

from petrunin.zena.mcpserver.src.qdrant.retriever_faq_services import (
    retriver_hybrid_async,
    QDRANT_COLLECTION_SERVICES,
    QDRANT_COLLECTION_FAQ
)

from petrunin.zena.mcpserver.src.qdrant.retriever_product import (
     retriever_product_hybrid_async
)

@pytest.mark.asyncio
@pytest.mark.parametrize("channel_id", [1, 2])
async def test_retriver_hybrid_async_services(channel_id):
    results = await retriver_hybrid_async(
        query="Массаж",
        database_name=QDRANT_COLLECTION_SERVICES,
        channel_id=channel_id
    )
    assert isinstance(results, list)
    assert len(results) > 0, f"Результаты для channel_id={channel_id} должны быть не пустыми"


@pytest.mark.asyncio
@pytest.mark.parametrize("channel_id", [1, 2])
async def test_retriver_hybrid_async_faq(channel_id):
    results = await retriver_hybrid_async(
        query="Абонемент",
        database_name=QDRANT_COLLECTION_FAQ,
        channel_id=channel_id
    )
    assert isinstance(results, list)
    assert len(results) > 0, f"Результаты для channel_id={channel_id} должны быть не пустыми"


@pytest.mark.asyncio
@pytest.mark.parametrize("channel_id", [1, 2])
async def test_retriever_product_hybrid_async(channel_id):
    results = await retriever_product_hybrid_async(
        channel_id=channel_id,
        query="массаж",
        indications=["отечность"],
        contraindications=["высокое"],
        body_parts=["тело"],
        # product_type=["разовый"]
    )
    assert isinstance(results, list)
    assert len(results) > 0, f"Результаты для channel_id={channel_id} должны быть не пустыми"