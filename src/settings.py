# src/settings.py
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _str(name: str, default: str | None = None, *, required: bool = False) -> str:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        if required:
            raise RuntimeError(f"Missing required env var: {name}")
        if default is None:
            return ""
        return default
    return v.strip()


def _int(name: str, default: int | None = None, *, required: bool = False) -> int:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        if required:
            raise RuntimeError(f"Missing required env var: {name}")
        if default is None:
            raise RuntimeError(f"Missing env var (no default): {name}")
        return default
    try:
        return int(v)
    except ValueError as e:
        raise RuntimeError(f"Invalid int env var {name}={v!r}") from e


def _float(name: str, default: float | None = None, *, required: bool = False) -> float:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        if required:
            raise RuntimeError(f"Missing required env var: {name}")
        if default is None:
            raise RuntimeError(f"Missing env var (no default): {name}")
        return default
    try:
        return float(v)
    except ValueError as e:
        raise RuntimeError(f"Invalid float env var {name}={v!r}") from e


@dataclass(frozen=True, slots=True)
class Settings:
    # Runtime
    ENV: str
    LOG_LEVEL: str

    # CRM
    CRM_BASE_URL: str
    CRM_HTTP_TIMEOUT_S: float
    CRM_HTTP_RETRIES: int
    CRM_RETRY_MIN_DELAY_S: float
    CRM_RETRY_MAX_DELAY_S: float

    # Postgres
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    PG_POOL_MIN: int
    PG_POOL_MAX: int
    PG_CONNECT_TIMEOUT_S: int
    PG_STATEMENT_TIMEOUT_MS: int
    PG_QUERY_TIMEOUT_S: int

    # Qdrant
    QDRANT_URL: str
    QDRANT_TIMEOUT: float
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_FAQ: str
    QDRANT_COLLECTION_SERVICES: str
    QDRANT_COLLECTION_PRODUCTS: str
    QDRANT_COLLECTION_TEMP: str

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_TIMEOUT_S: float
    OPENAI_PROXY_URL: str
    OPENAI_MODEL: str
    OPENAI_TEMPERATURE: float


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Runtime
    env = _str("ENV", "dev")
    log_level = _str("LOG_LEVEL", "INFO")

    # CRM
    crm_base_url = _str("CRM_BASE_URL", "https://httpservice.ai2b.pro").rstrip("/")
    crm_timeout = _float("CRM_HTTP_TIMEOUT_S", 180.0)
    crm_retries = _int("CRM_HTTP_RETRIES", 3)
    crm_min_delay = _float("CRM_RETRY_MIN_DELAY_S", 1.0)
    crm_max_delay = _float("CRM_RETRY_MAX_DELAY_S", 10.0)

    # Postgres (обязательные)
    pg_host = _str("POSTGRES_HOST", required=True)
    pg_port = _int("POSTGRES_PORT", required=True)
    pg_db = _str("POSTGRES_DB", required=True)
    pg_user = _str("POSTGRES_USER", required=True)
    pg_pass = _str("POSTGRES_PASSWORD", required=True)

    # Postgres (опциональные)
    pg_pool_min = _int("PG_POOL_MIN", 1)
    pg_pool_max = _int("PG_POOL_MAX", 10)
    pg_connect_timeout = _int("PG_CONNECT_TIMEOUT_S", 10)
    pg_stmt_timeout = _int("PG_STATEMENT_TIMEOUT_MS", 5000)
    pg_query_timeout = _int("PG_QUERY_TIMEOUT_S", 10)

    # Qdrant
    qdrant_url = _str("QDRANT_URL", required=True)
    qdrant_timeout = _float("QDRANT_TIMEOUT", 120.0)
    qdrant_api_key = _str("QDRANT_API_KEY", "")
    qdrant_faq = _str("QDRANT_COLLECTION_FAQ", required=True)
    qdrant_services = _str("QDRANT_COLLECTION_SERVICES", required=True)
    qdrant_products = _str("QDRANT_COLLECTION_PRODUCTS", required=True)
    qdrant_temp = _str("QDRANT_COLLECTION_TEMP", required=True)

    # OpenAI (ключ обычно обязателен в prod; в dev можно оставить пустым, если хотите)
    openai_key = _str("OPENAI_API_KEY", "")
    openai_timeout = _float("OPENAI_TIMEOUT_S", _float("OPENAI_TIMEOUT", 60.0))
    openai_proxy = _str("OPENAI_PROXY_URL", "")
    openai_model = _str("OPENAI_MODEL", "gpt-4o-mini")
    openai_temp = _float("OPENAI_TEMPERATURE", 0.2)

    return Settings(
        ENV=env,
        LOG_LEVEL=log_level,

        CRM_BASE_URL=crm_base_url,
        CRM_HTTP_TIMEOUT_S=crm_timeout,
        CRM_HTTP_RETRIES=crm_retries,
        CRM_RETRY_MIN_DELAY_S=crm_min_delay,
        CRM_RETRY_MAX_DELAY_S=crm_max_delay,

        POSTGRES_HOST=pg_host,
        POSTGRES_PORT=pg_port,
        POSTGRES_DB=pg_db,
        POSTGRES_USER=pg_user,
        POSTGRES_PASSWORD=pg_pass,
        PG_POOL_MIN=pg_pool_min,
        PG_POOL_MAX=pg_pool_max,
        PG_CONNECT_TIMEOUT_S=pg_connect_timeout,
        PG_STATEMENT_TIMEOUT_MS=pg_stmt_timeout,
        PG_QUERY_TIMEOUT_S=pg_query_timeout,

        QDRANT_URL=qdrant_url,
        QDRANT_TIMEOUT=qdrant_timeout,
        QDRANT_API_KEY=qdrant_api_key,
        QDRANT_COLLECTION_FAQ=qdrant_faq,
        QDRANT_COLLECTION_SERVICES=qdrant_services,
        QDRANT_COLLECTION_PRODUCTS=qdrant_products,
        QDRANT_COLLECTION_TEMP=qdrant_temp,

        OPENAI_API_KEY=openai_key,
        OPENAI_TIMEOUT_S=openai_timeout,
        OPENAI_PROXY_URL=openai_proxy,
        OPENAI_MODEL=openai_model,
        OPENAI_TEMPERATURE=openai_temp,
    )
