# src/http_retry.py
from __future__ import annotations

"""
Единый механизм повторов (retry) для HTTP-запросов.

Проблема, которую решаем
------------------------
Раньше модуль делал так:

    S = get_settings()
    CRM_HTTP_RETRY = retry(... S.CRM_HTTP_RETRIES ...)

Это означает:
- get_settings() вызывается при ИМПОРТЕ модуля src.http_retry
- если env ещё не загружен (init_runtime() не вызывался), то:
  - можно получить неправильные значения
  - или упасть при старте (missing required env)

Решение
-------
Сделать декоратор ЛЕНИВЫМ:
- настройки читаем только когда декоратор реально нужен
- конфиг retry создаём один раз и кешируем (lru_cache)

При этом внешний API остаётся тем же:
    from src.http_retry import CRM_HTTP_RETRY

    @CRM_HTTP_RETRY
    async def my_call(...):
        ...
"""

import logging
from functools import lru_cache
from typing import Any, Callable, TypeVar, cast

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from src.settings import get_settings

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _is_retryable(exc: BaseException) -> bool:
    """Правило: что ретраим, а что нет."""
    # Сеть/таймауты — ретраим
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True

    # Плохой HTTP-статус после raise_for_status()
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        # Ретраим 429 и 5xx
        return status == 429 or 500 <= status < 600

    # Остальное — не ретраим
    return False


@lru_cache(maxsize=1)
def _get_crm_retry_decorator():
    """
    Создаёт и кеширует настроенный tenacity.retry декоратор.

    Важно:
    - вызывается один раз при первом использовании
    - settings читаем здесь, а не при импорте файла
    """
    s = get_settings()

    def _log_before_sleep(rs) -> None:
        """Логируем перед тем, как tenacity подождёт и повторит."""
        exc = rs.outcome.exception()
        logger.warning(
            "HTTP retry: %r | attempt=%s/%s sleep=%.1fs",
            exc,
            rs.attempt_number,
            s.CRM_HTTP_RETRIES,
            rs.next_action.sleep,
        )

    return retry(
        reraise=True,
        stop=stop_after_attempt(s.CRM_HTTP_RETRIES),
        wait=wait_exponential_jitter(
            initial=s.CRM_RETRY_MIN_DELAY_S,
            max=s.CRM_RETRY_MAX_DELAY_S,
        ),
        retry=retry_if_exception(_is_retryable),
        before_sleep=_log_before_sleep,
    )


def CRM_HTTP_RETRY(fn: F) -> F:
    """
    Публичный "декоратор", который выглядит как tenacity.retry,
    но фактически создаёт tenacity-конфиг лениво.

    Использование не меняется:
        @CRM_HTTP_RETRY
        async def call(...): ...
    """
    dec = _get_crm_retry_decorator()
    return cast(F, dec(fn))
