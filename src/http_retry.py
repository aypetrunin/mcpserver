"""Ленивый retry-декоратор для HTTP-вызовов на базе tenacity.

Настройки читаются только при первом использовании декоратора
и кэшируются, чтобы избежать доступа к env при импорте модуля.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
import logging
from typing import Any, TypeVar, cast

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.settings import get_settings


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _is_retryable(exc: BaseException) -> bool:
    """Определяет, является ли исключение ретраябельным."""
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or 500 <= status < 600

    return False


@lru_cache(maxsize=1)
def _get_crm_retry_decorator() -> Callable[[F], F]:
    """Создаёт и кэширует настроенный retry-декоратор."""
    s = get_settings()

    def _log_before_sleep(rs: RetryCallState) -> None:
        """Логирует паузу перед повторной попыткой."""
        exc = rs.outcome.exception()
        logger.warning(
            "HTTP retry: %r | attempt=%s/%s sleep=%.1fs",
            exc,
            rs.attempt_number,
            s.CRM_HTTP_RETRIES,
            rs.next_action.sleep,
        )

    dec = retry(
        reraise=True,
        stop=stop_after_attempt(s.CRM_HTTP_RETRIES),
        wait=wait_exponential_jitter(
            initial=s.CRM_RETRY_MIN_DELAY_S,
            max=s.CRM_RETRY_MAX_DELAY_S,
        ),
        retry=retry_if_exception(_is_retryable),
        before_sleep=_log_before_sleep,
    )
    return cast(Callable[[F], F], dec)


def CRM_HTTP_RETRY(fn: F) -> F:
    """Оборачивает функцию в лениво-настроенный retry-декоратор."""
    dec = _get_crm_retry_decorator()
    return dec(fn)
