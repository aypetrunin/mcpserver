"""Модуль общих функций для retriever_faq_services, retriever_product."""

import asyncio
import inspect
import logging
import os
import random
from pathlib import Path
from typing import Callable, TypeVar, Any, Awaitable, Iterator, Iterable


import httpx
from dotenv import load_dotenv
from fastembed.sparse.bm25 import Bm25
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.models import TextIndexType

# -------------------- Logging --------------------
# Настройка логирования для вывода сообщений в консоль
logging.basicConfig(
    level=logging.INFO,  # минимальный уровень логирования INFO
    format="%(asctime)s [%(levelname)s] %(message)s",  # формат: время [уровень] сообщение
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)  # создаём логгер для текущего модуля

# -------------------- Load env --------------------
# Загружаем переменные окружения из файла .env
if not os.getenv("IS_DOCKER"):
    ROOT = Path(__file__).resolve().parents[3]
    dotenv_path = ROOT / "deploy" / "dev.env"
    load_dotenv(dotenv_path=dotenv_path)
    
# -------------------- Config --------------------
# Конфигурация для OpenAI, Qdrant и Postgres
OPENAI_PROXY = os.getenv("OPENAI_PROXY_URL")  # Прокси для OpenAI (если нужен)
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "60"))  # Таймаут запросов к OpenAI
QDRANT_URL = os.getenv("QDRANT_URL", "172.17.0.1:6333")  # URL Qdrant
QDRANT_TIMEOUT = int(os.getenv("QDRANT_TIMEOUT", "120"))  # Таймаут запросов к Qdrant

# Конфигурация для подключения к PostgreSQL
POSTGRES_CONFIG = {
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "database": os.getenv("POSTGRES_DB"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT"),
}

# -------------------- Clients --------------------
# Инициализация клиентов для работы с разными сервисами

# BM25 sparse embedding модель для поиска по тексту
bm25_embedding_model = Bm25("Qdrant/bm25", language="russian")

# Асинхронный клиент OpenAI с использованием httpx
openai_client = AsyncOpenAI(
    http_client=httpx.AsyncClient(proxy=OPENAI_PROXY, timeout=OPENAI_TIMEOUT)
)

# Асинхронный клиент Qdrant для работы с векторной базой данных
qdrant_client = AsyncQdrantClient(
    QDRANT_URL, timeout=QDRANT_TIMEOUT, check_compatibility=False
)


T = TypeVar("T")
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
# Генератор для разбиения любого итерируемого объекта на батчи заданного размера
def batch_iterable(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    """Генератор для разбиения любого итерируемого объекта на батчи заданного размера."""
    lst = list(iterable)  # ← Конвертируем в list
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


# -------------------- Embeddings --------------------
# Асинхронная функция для получения векторных представлений текстов
async def embed_texts(
    texts: list[str], model: str, dimensions: int | None = None
) -> list[list[float]]:
    """функция для получения векторных представлений текстов."""
    # Убираем пустые строки и заменяем переносы строк на пробелы
    texts = [t.replace("\n", " ") for t in texts if t and t.strip()]
    if not texts:
        return []  # если нет текста, возвращаем пустой список
    # Получаем эмбеддинги через OpenAI с повторными попытками
    response = await retry_request(
        openai_client.embeddings.create,
        input=texts,
        model=model,
        **(
            {"dimensions": dimensions} if dimensions else {}
        ),  # передаем размерность, если указана
    )
    # Возвращаем список векторов
    return [item.embedding for item in response.data]


# Обертка для стандартной модели ada
async def ada_embeddings(
        texts: list[str],
        model: str = "text-embedding-ada-002"
) -> list[list[float]]:
    """Обертка для стандартной модели ada."""
    return await embed_texts(texts, model=model)


# -------------------- Reset collection --------------------
# Функция для удаления и создания коллекции в Qdrant с настройкой векторов и индексов
async def reset_collection(
    client: AsyncQdrantClient,
    collection_name: str,
    text_index_fields: list[str] | None = None,  # поля для текстового поиска
) -> None:
    """Функция для удаления и создания коллекции."""
    try:
        # Пробуем удалить коллекцию (если она существует)
        await client.delete_collection(collection_name)
        logger.info(f'Коллекция "{collection_name}" удалена.')
    except Exception:
        logger.warning(f'Коллекция "{collection_name}" не найдена или ошибка удаления.')

    # Создаем новую коллекцию с конфигурацией HNSW и векторных пространств
    await client.create_collection(
        collection_name,
        hnsw_config=models.HnswConfigDiff(
            m=32,  # параметр HNSW: количество соседей для построения графа
            ef_construct=200,  # точность построения индекса
            full_scan_threshold=50000,  # порог для полного сканирования вместо индекса
            max_indexing_threads=4,  # количество потоков для индексации
        ),
        vectors_config={
            "ada-embedding": models.VectorParams(
                size=1536,  # размерность эмбеддинга
                distance=models.Distance.COSINE,  # метрика косинусного сходства
                datatype=models.Datatype.FLOAT16,  # тип хранения
            ),
        },
        sparse_vectors_config={
            "bm25": models.SparseVectorParams(
                modifier=models.Modifier.IDF,  # модификатор BM25
                index=models.SparseIndexParams(),  # параметры sparse индекса
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


    # # Создаем текстовые индексы для указанных полей
    # if text_index_fields:
    #     default_text_index_params = {
    #         "type": "text",
    #         "tokenizer": models.TokenizerType.WORD,
    #         "min_token_len": 1,
    #         "max_token_len": 15,
    #         "lowercase": True,
    #     }
    #     for field in text_index_fields:
    #         await client.create_payload_index(
    #             collection_name=collection_name,
    #             field_name=field,
    #             field_schema=models.TextIndexParams(**default_text_index_params),
    #         )
    #         logger.info(f'Индекс "{field}" создан.')
