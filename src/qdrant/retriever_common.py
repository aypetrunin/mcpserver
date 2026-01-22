# retriever_common.py

# retriever_common.py
"""Модуль общих функций для retriever_faq_services, retriever_product."""

import asyncio
import inspect
import logging
import random
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Iterator, TypeVar

import httpx
from fastembed.sparse.bm25 import Bm25
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.models import TextIndexType

from src.settings import get_settings

T = TypeVar("T")

# -------------------- Logging --------------------
logger = logging.getLogger(__name__)

# -------------------- Clients --------------------
_openai_http: httpx.AsyncClient | None = None
_openai_client: AsyncOpenAI | None = None
_qdrant_client: AsyncQdrantClient | None = None
_bm25_model: Bm25 | None = None


# BM25 sparse embedding модель для поиска по тексту
def get_bm25_model() -> Bm25:
    global _bm25_model
    if _bm25_model is None:
        _bm25_model = Bm25("Qdrant/bm25", language="russian")
    return _bm25_model


def get_openai_client() -> AsyncOpenAI:
    global _openai_http, _openai_client

    if _openai_client is None:
        s = get_settings()
        proxy = s.OPENAI_PROXY_URL or None
        timeout = float(s.OPENAI_TIMEOUT_S)

        _openai_http = httpx.AsyncClient(proxy=proxy, timeout=timeout)
        _openai_client = AsyncOpenAI(http_client=_openai_http)

    return _openai_client


def get_qdrant_client() -> AsyncQdrantClient:
    global _qdrant_client

    if _qdrant_client is None:
        s = get_settings()
        url = s.QDRANT_URL
        timeout = float(s.QDRANT_TIMEOUT)

        _qdrant_client = AsyncQdrantClient(url=url, timeout=timeout)

    return _qdrant_client


async def close_clients() -> None:
    # вызывать на shutdown (по желанию, но правильно)
    global _openai_http, _openai_client, _qdrant_client

    if _openai_http is not None:
        await _openai_http.aclose()

    _openai_http = None
    _openai_client = None
    _qdrant_client = None


# -------------------- Retry helper --------------------
# Универсальная функция с повторной попыткой для асинхронных
async def retry_request(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    retries: int = 3,
    backoff: float = 2.0,
    **kwargs: Any,
) -> T:
    for attempt in range(1, retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == retries:
                logger.exception(f"Последняя попытка {func.__name__}: {e}")
                raise
            wait = backoff**attempt + random.uniform(0, 1)
            logger.warning(f"Ошибка {func.__name__}: {e} | {attempt}/{retries}")
            await asyncio.sleep(wait)
    raise RuntimeError("Retry исчерпан")


# -------------------- Batch helper --------------------
def batch_iterable(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    """Генератор для разбиения любого итерируемого объекта на батчи заданного размера."""
    lst = list(iterable)
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


# -------------------- Embeddings --------------------
async def embed_texts(
    texts: list[str], model: str, dimensions: int | None = None
) -> list[list[float]]:
    """функция для получения векторных представлений текстов."""
    texts = [t.replace("\n", " ") for t in texts if t and t.strip()]
    if not texts:
        return []

    response = await retry_request(
        get_openai_client().embeddings.create,
        input=texts,
        model=model,
        **({"dimensions": dimensions} if dimensions else {}),
    )
    return [item.embedding for item in response.data]


async def ada_embeddings(texts: list[str], model: str = "text-embedding-ada-002") -> list[list[float]]:
    """Обертка для стандартной модели ada."""
    return await embed_texts(texts, model=model)


# -------------------- Reset collection --------------------
async def reset_collection(
    client: AsyncQdrantClient,
    collection_name: str,
    text_index_fields: list[str] | None = None,
) -> None:
    """Функция для удаления и создания коллекции."""
    try:
        await client.delete_collection(collection_name)
        logger.info(f'Коллекция "{collection_name}" удалена.')
    except Exception:
        logger.warning(f'Коллекция "{collection_name}" не найдена или ошибка удаления.')

    await client.create_collection(
        collection_name,
        hnsw_config=models.HnswConfigDiff(
            m=32,
            ef_construct=200,
            full_scan_threshold=50000,
            max_indexing_threads=4,
        ),
        vectors_config={
            "ada-embedding": models.VectorParams(
                size=1536,
                distance=models.Distance.COSINE,
                datatype=models.Datatype.FLOAT16,
            ),
        },
        sparse_vectors_config={
            "bm25": models.SparseVectorParams(
                modifier=models.Modifier.IDF,
                index=models.SparseIndexParams(),
            ),
        },
    )
    logger.info(f'Коллекция "{collection_name}" создана.')

    if text_index_fields:
        for field in text_index_fields:
            await client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=models.TextIndexParams(
                    type=TextIndexType.TEXT,
                    tokenizer=models.TokenizerType.WORD,
                    min_token_len=1,
                    max_token_len=15,
                    lowercase=True,
                ),
            )
            logger.info(f'Индекс "{field}" создан.')








# """Модуль общих функций для retriever_faq_services, retriever_product."""

# import asyncio
# import inspect
# import logging
# import os
# import random
# from pathlib import Path
# from typing import Callable, TypeVar, Any, Awaitable, Iterator, Iterable


# import httpx
# from fastembed.sparse.bm25 import Bm25
# from openai import AsyncOpenAI
# from qdrant_client import AsyncQdrantClient, models
# from qdrant_client.http.models import TextIndexType


# T = TypeVar("T")
# # -------------------- Logging --------------------
# # Настройка логирования для вывода сообщений в консоль

# logger = logging.getLogger(__name__)

# def get_postgres_config() -> dict[str, str | None]:
#     return {
#         "user": os.getenv("POSTGRES_USER"),
#         "password": os.getenv("POSTGRES_PASSWORD"),
#         "database": os.getenv("POSTGRES_DB"),
#         "host": os.getenv("POSTGRES_HOST"),
#         "port": os.getenv("POSTGRES_PORT"),
#     }

# # -------------------- Clients --------------------
# # Инициализация клиентов для работы с разными сервисами

# _openai_http: httpx.AsyncClient | None = None
# _openai_client: AsyncOpenAI | None = None
# _qdrant_client: AsyncQdrantClient | None = None
# _bm25_model: Bm25 | None = None

# # BM25 sparse embedding модель для поиска по тексту
# def get_bm25_model() -> Bm25:
#     global _bm25_model
#     if _bm25_model is None:
#         _bm25_model = Bm25("Qdrant/bm25", language="russian")
#     return _bm25_model


# def get_openai_client() -> AsyncOpenAI:
#     global _openai_http, _openai_client

#     if _openai_client is None:
#         proxy = os.getenv("OPENAI_PROXY_URL")
#         timeout = float(os.getenv("OPENAI_TIMEOUT", "60"))

#         _openai_http = httpx.AsyncClient(proxy=proxy, timeout=timeout)
#         _openai_client = AsyncOpenAI(http_client=_openai_http)

#     return _openai_client


# def get_qdrant_client() -> AsyncQdrantClient:
#     global _qdrant_client

#     if _qdrant_client is None:
#         url = os.getenv("QDRANT_URL")
#         timeout = float(os.getenv("QDRANT_TIMEOUT", "120"))
#         _qdrant_client = AsyncQdrantClient(url=url, timeout=timeout)

#     return _qdrant_client


# async def close_clients() -> None:
#     # вызывать на shutdown (по желанию, но правильно)
#     global _openai_http, _openai_client, _qdrant_client

#     if _openai_http is not None:
#         await _openai_http.aclose()

#     _openai_http = None
#     _openai_client = None
#     _qdrant_client = None

# # -------------------- Retry helper --------------------
# # Универсальная функция с повторной попыткой для асинхронных
# async def retry_request(
#     func: Callable[..., Awaitable[T]],
#     *args: Any,
#     retries: int = 3,
#     backoff: float = 2.0,
#     **kwargs: Any,
# ) -> T:
#     for attempt in range(1, retries + 1):
#         try:
#             return await func(*args, **kwargs)
#         except Exception as e:
#             if attempt == retries:
#                 logger.exception(f"Последняя попытка {func.__name__}: {e}")
#                 raise
#             wait = backoff**attempt + random.uniform(0, 1)
#             logger.warning(f"Ошибка {func.__name__}: {e} | {attempt}/{retries}")
#             await asyncio.sleep(wait)
#     raise RuntimeError("Retry исчерпан")


# # -------------------- Batch helper --------------------
# # Генератор для разбиения любого итерируемого объекта на батчи заданного размера
# def batch_iterable(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
#     """Генератор для разбиения любого итерируемого объекта на батчи заданного размера."""
#     lst = list(iterable)  # ← Конвертируем в list
#     for i in range(0, len(lst), size):
#         yield lst[i : i + size]


# # -------------------- Embeddings --------------------
# # Асинхронная функция для получения векторных представлений текстов
# async def embed_texts(
#     texts: list[str], model: str, dimensions: int | None = None
# ) -> list[list[float]]:
#     """функция для получения векторных представлений текстов."""
#     # Убираем пустые строки и заменяем переносы строк на пробелы
#     texts = [t.replace("\n", " ") for t in texts if t and t.strip()]
#     if not texts:
#         return []  # если нет текста, возвращаем пустой список
#     # Получаем эмбеддинги через OpenAI с повторными попытками
#     response = await retry_request(
#         get_openai_client().embeddings.create,
#         input=texts,
#         model=model,
#         **(
#             {"dimensions": dimensions} if dimensions else {}
#         ),  # передаем размерность, если указана
#     )
#     # Возвращаем список векторов
#     return [item.embedding for item in response.data]


# # Обертка для стандартной модели ada
# async def ada_embeddings(
#         texts: list[str],
#         model: str = "text-embedding-ada-002"
# ) -> list[list[float]]:
#     """Обертка для стандартной модели ada."""
#     return await embed_texts(texts, model=model)


# # -------------------- Reset collection --------------------
# # Функция для удаления и создания коллекции в Qdrant с настройкой векторов и индексов
# async def reset_collection(
#     client: AsyncQdrantClient,
#     collection_name: str,
#     text_index_fields: list[str] | None = None,  # поля для текстового поиска
# ) -> None:
#     """Функция для удаления и создания коллекции."""
#     try:
#         # Пробуем удалить коллекцию (если она существует)
#         await client.delete_collection(collection_name)
#         logger.info(f'Коллекция "{collection_name}" удалена.')
#     except Exception:
#         logger.warning(f'Коллекция "{collection_name}" не найдена или ошибка удаления.')

#     # Создаем новую коллекцию с конфигурацией HNSW и векторных пространств
#     await client.create_collection(
#         collection_name,
#         hnsw_config=models.HnswConfigDiff(
#             m=32,  # параметр HNSW: количество соседей для построения графа
#             ef_construct=200,  # точность построения индекса
#             full_scan_threshold=50000,  # порог для полного сканирования вместо индекса
#             max_indexing_threads=4,  # количество потоков для индексации
#         ),
#         vectors_config={
#             "ada-embedding": models.VectorParams(
#                 size=1536,  # размерность эмбеддинга
#                 distance=models.Distance.COSINE,  # метрика косинусного сходства
#                 datatype=models.Datatype.FLOAT16,  # тип хранения
#             ),
#         },
#         sparse_vectors_config={
#             "bm25": models.SparseVectorParams(
#                 modifier=models.Modifier.IDF,  # модификатор BM25
#                 index=models.SparseIndexParams(),  # параметры sparse индекса
#             ),
#         },
#     )
#     logger.info(f'Коллекция "{collection_name}" создана.')

#     if text_index_fields:
#         for field in text_index_fields:
#             await client.create_payload_index(
#                 collection_name=collection_name,
#                 field_name=field,
#                 field_schema=models.TextIndexParams(
#                     type=TextIndexType.TEXT,
#                     tokenizer=models.TokenizerType.WORD,
#                     min_token_len=1,
#                     max_token_len=15,
#                     lowercase=True,
#                 ),
#             )
#             logger.info(f'Индекс "{field}" создан.')
