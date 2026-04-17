"""Единая настройка логирования и профилирования для mcpserver.

Предоставляет:
- setup_logging() — инициализация structlog (JSON в prod, цветной текст в dev).
- get_logger() — получение bound logger с контекстом из contextvars.
- timed(operation) — декоратор для профилирования async-функций.
- timed_block(operation) — контекстный менеджер для профилирования блоков кода.
- with_tracing — декоратор для MCP-инструментов: извлекает _request_id, привязывает к contextvars.
- bind_contextvars / clear_contextvars — привязка контекста запроса.
"""

import functools
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars  # noqa: F401

SENSITIVE_KEYS = {"phone", "access_token", "session_id", "email"}


def _mask_pii_processor(
    logger: Any, method: str, event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Маскирует значения чувствительных полей (prod only)."""
    for key in SENSITIVE_KEYS:
        if key in event_dict:
            val = str(event_dict[key])
            event_dict[key] = val[:3] + "***" + val[-3:] if len(val) > 6 else "***"
    return event_dict


def _noop(
    logger: Any, method: str, event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Пропускает event_dict без изменений (dev — без маскирования)."""
    return event_dict


def _request_id_first(
    logger: Any, method: str, event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Ставит request_id первым полем в event_dict."""
    rid = event_dict.pop("request_id", None)
    if rid is not None:
        event_dict = {"request_id": rid, **event_dict}
    return event_dict


def setup_logging() -> None:
    """Настройка structlog. Вызывается один раз при старте сервиса."""
    log_format = os.getenv("LOG_FORMAT", "").strip().lower()
    env = os.getenv("ENV", "prod").strip().lower()
    is_dev = env == "dev" and log_format != "json"

    level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    # stdlib root logger по умолчанию WARNING без handlers — это молча проглатывает
    # INFO-события structlog-а. Без этого вызова docker logs покажет только
    # uvicorn access (у него свой handler), а наши log.info(...) будут не видны.
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(message)s",
        force=True,
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _request_id_first,
        _noop if is_dev else _mask_pii_processor,
        structlog.dev.ConsoleRenderer() if is_dev
        else structlog.processors.JSONRenderer(),
    ]
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(**kwargs: Any) -> structlog.stdlib.BoundLogger:
    """Возвращает bound logger с переданными начальными полями."""
    return structlog.get_logger(**kwargs)


def timed(operation: str) -> Any:
    """Декоратор: логирует duration_sec для async-функции."""
    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            log = get_logger()
            t0 = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = round(time.perf_counter() - t0, 3)
                log.info("operation.completed", operation=operation, duration_sec=duration)
                return result
            except Exception as e:
                duration = round(time.perf_counter() - t0, 3)
                log.error("operation.failed", operation=operation, duration_sec=duration, error=str(e))
                raise
        return wrapper
    return decorator


@asynccontextmanager
async def timed_block(operation: str) -> AsyncIterator[None]:
    """Контекстный менеджер: логирует duration_sec для блока кода."""
    log = get_logger()
    t0 = time.perf_counter()
    try:
        yield
    finally:
        duration = round(time.perf_counter() - t0, 3)
        log.info("operation.completed", operation=operation, duration_sec=duration)


def with_tracing(func: Any) -> Any:
    """Декоратор для MCP-инструментов: извлекает _request_id и привязывает к contextvars.

    Использование:
        @mcp.tool()
        @with_tracing
        async def some_tool(arg1: str, arg2: int) -> Payload:
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request_id = kwargs.pop("_request_id", "")
        clear_contextvars()
        bind_contextvars(request_id=request_id)
        log = get_logger()
        log.info("tool.started", tool=func.__name__)
        t0 = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            duration = round(time.perf_counter() - t0, 3)
            log.info("tool.completed", tool=func.__name__, duration_sec=duration)
            return result
        except Exception as e:
            duration = round(time.perf_counter() - t0, 3)
            log.error("tool.failed", tool=func.__name__, duration_sec=duration, error=str(e))
            raise
    return wrapper
