# src/http_retry.py
from __future__ import annotations

"""
Назначение (для новичка)
========================
Этот файл задаёт единый механизм повторов (retry) для HTTP-запросов.

Почему здесь читаем settings при импорте?
----------------------------------------
В вашем проекте init_runtime() вызывается в main ДО импорта/использования бизнес-кода,
поэтому переменные окружения уже готовы.
Это позволяет:
- не передавать attempts/min/max по всему проекту
- держать стандарт retry в одном месте
- менять поведение через env без правок кода

Что экспортируем:
-----------------
- CRM_HTTP_RETRY — готовый декоратор retry с параметрами из settings.

Как использовать:
-----------------
from src.http_retry import CRM_HTTP_RETRY

@CRM_HTTP_RETRY
async def my_http_call(...):
    ...
"""

import logging

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from src.settings import get_settings

logger = logging.getLogger(__name__)

# Читаем настройки ОДИН раз.
# Благодаря lru_cache внутри get_settings() это быстро и безопасно.
S = get_settings()


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


def _log_before_sleep(rs) -> None:
    """Логируем перед тем, как tenacity подождёт и повторит."""
    exc = rs.outcome.exception()
    logger.warning(
        "HTTP retry: %r | attempt=%s/%s sleep=%.1fs",
        exc,
        rs.attempt_number,
        S.CRM_HTTP_RETRIES,
        rs.next_action.sleep,
    )


# ✅ Готовый декоратор для всех "CRM/HTTPService" запросов проекта
CRM_HTTP_RETRY = retry(
    reraise=True,
    stop=stop_after_attempt(S.CRM_HTTP_RETRIES),
    wait=wait_exponential_jitter(initial=S.CRM_RETRY_MIN_DELAY_S, max=S.CRM_RETRY_MAX_DELAY_S),
    retry=retry_if_exception(_is_retryable),
    before_sleep=_log_before_sleep,
)
