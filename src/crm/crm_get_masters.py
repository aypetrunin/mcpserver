# crm_get_masters.py
"""Модуль получения списка мастеров из CRM."""

import logging
from typing import Any, TypedDict, Literal, cast

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .crm_settings import (
    CRM_BASE_URL,
    CRM_HTTP_TIMEOUT_S,
    CRM_HTTP_RETRIES,
    CRM_RETRY_MIN_DELAY_S,
    CRM_RETRY_MAX_DELAY_S,
)

from .crm_result import Payload, ok, err


logger = logging.getLogger(__name__)


# -------------------- Типы ответа CRM --------------------

class Master(TypedDict, total=False):
    id: int
    name: str


class MastersOk(TypedDict):
    success: Literal[True]
    masters: list[Master]


# -------------------- Основная функция --------------------

@retry(
    stop=stop_after_attempt(CRM_HTTP_RETRIES),
    wait=wait_exponential(
        multiplier=1,
        min=CRM_RETRY_MIN_DELAY_S,
        max=CRM_RETRY_MAX_DELAY_S,
    ),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def get_masters(
    channel_id: int,
    timeout: float = CRM_HTTP_TIMEOUT_S,
) -> Payload[list[Master]]:
    """
    Получить список мастеров для канала.

    Возвращает:
    - ok(list[Master]) — при успехе
    - err(...)         — при ошибке
    """
    logger.info("===crm.get_masters===")
    logger.info("Получение списка мастеров channel_id=%s", channel_id)

    url = f"{CRM_BASE_URL}/appointments/yclients/staff/actual"
    payload = {"channel_id": channel_id}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info("POST %s payload=%r", url, payload)
            response = await client.post(url, json=payload)
            response.raise_for_status()

            # Any допустим ТОЛЬКО здесь
            resp_any: Any = response.json()

    except httpx.TimeoutException as e:
        # timeout / connect ошибки → retry через tenacity
        logger.warning("Таймаут при получении мастеров channel_id=%s: %s", channel_id, e)
        raise

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP %s при получении мастеров channel_id=%s",
            e.response.status_code,
            channel_id,
        )
        return err(
            code="http_error",
            error=f"CRM вернул HTTP {e.response.status_code}",
        )

    except Exception as e:  # noqa: BLE001
        logger.exception(
            "Неожиданная ошибка при получении мастеров channel_id=%s", channel_id
        )
        return err(
            code="unexpected_error",
            error="Неизвестная ошибка при получении списка мастеров",
        )

    # -------------------- Валидация ответа CRM --------------------

    if not isinstance(resp_any, dict):
        return err(
            code="crm_bad_response",
            error="CRM вернул некорректный JSON",
        )

    resp = cast(dict[str, Any], resp_any)

    if not resp.get("success", False):
        return err(
            code="crm_error",
            error="CRM вернул ошибку при получении мастеров",
        )

    masters_raw = resp.get("masters")
    if not isinstance(masters_raw, list):
        return err(
            code="crm_bad_response",
            error="CRM вернул некорректный список мастеров",
        )

    masters: list[Master] = []
    for item in masters_raw:
        if isinstance(item, dict):
            masters.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                }
            )

    return ok(masters)
