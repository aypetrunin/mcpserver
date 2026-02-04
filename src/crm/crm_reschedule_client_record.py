# src/crm/crm_reschedule_client_record.py
from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict

import httpx

from src.clients import get_http
from src.http_retry import CRM_HTTP_RETRY
from src.crm.crm_http import crm_timeout_s, crm_url

logger = logging.getLogger(__name__)

RESCHEDULE_PATH = "/appointments/client/records/reschedule"


class RescheduleClientRecordPayload(TypedDict):
    user_companychat: int
    channel_id: int
    record_id: int
    master_id: str
    date: str
    time: str
    comment: Optional[str]


class RescheduleClientRecordResponse(TypedDict, total=False):
    success: bool
    error: str
    details: str


async def reschedule_client_record(
    user_companychat: int,
    channel_id: int,
    record_id: int,
    master_id: int,
    date: str,
    time: str,
    comment: Optional[str] = "Автоперенос ботом через API",
    endpoint_url: Optional[str] = None,
    timeout: float = 0.0,
) -> dict[str, Any]:
    """
    Перенос услуги пользователя на другую дату и время.

    Важно:
    - НИКАКИХ get_settings() на уровне модуля.
    - URL и timeout считаются лениво:
        - если endpoint_url передан — используем его
        - иначе строим из settings в момент вызова
    """
    logger.info("=== crm.crm_reschedule_client_record ===")

    url = endpoint_url or crm_url(RESCHEDULE_PATH)
    effective_timeout = crm_timeout_s(timeout)

    payload: RescheduleClientRecordPayload = {
        "user_companychat": user_companychat,
        "channel_id": channel_id,
        "record_id": record_id,
        "master_id": str(master_id),
        "date": date,
        "time": time,
        "comment": comment,
    }

    logger.info("Подготовка переноса услуги payload=%s", payload)

    try:
        resp_json = await _reschedule_payload(url=url, payload=payload, timeout_s=effective_timeout)
        logger.info("Перенос услуги успешно выполнен payload=%s", payload)
        return resp_json

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        body = e.response.text

        logger.error("CRM HTTP %d. payload=%s body=%s", status, payload, body[:800])

        return {
            "success": False,
            "error": f"HTTP ошибка: {status}",
            "details": body[:800],
        }

    except httpx.RequestError as e:
        logger.error("Сетевая ошибка при переносе payload=%s: %s", payload, e)
        return {"success": False, "error": "network_error", "details": str(e)[:800]}

    except ValueError as e:
        logger.error("Некорректный ответ CRM при переносе payload=%s: %s", payload, e)
        return {"success": False, "error": "invalid_response", "details": str(e)[:800]}

    except Exception as e:  # noqa: BLE001
        logger.exception("Неожиданная ошибка при переносе payload=%s: %s", payload, e)
        return {"success": False, "error": "unknown_error"}


@CRM_HTTP_RETRY
async def _reschedule_payload(
    url: str,
    payload: RescheduleClientRecordPayload,
    timeout_s: float,
) -> dict[str, Any]:
    """
    Низкоуровневый HTTP-вызов с единым retry-поведением:
    - timeout / network error
    - HTTP 429
    - HTTP 5xx
    """
    client = get_http()

    logger.info("POST %s payload=%s", url, payload)
    resp = await client.post(url, json=payload, timeout=httpx.Timeout(timeout_s))
    resp.raise_for_status()

    try:
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Недопустимый ответ JSON от CRM: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Неожиданный тип JSON из CRM: {type(data)}")

    return data





# import logging
# from typing import Any, Dict, Optional

# import httpx
# from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# from .crm_settings import (
#     CRM_BASE_URL,
#     CRM_HTTP_TIMEOUT_S,
#     CRM_HTTP_RETRIES,
#     CRM_RETRY_MIN_DELAY_S,
#     CRM_RETRY_MAX_DELAY_S,
# )

# logger = logging.getLogger(__name__)

# @retry(
#     stop=stop_after_attempt(CRM_HTTP_RETRIES),
#     wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
#     retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.RequestError)),
#     reraise=True,
# )
# async def reschedule_client_record(
#     user_companychat: int,
#     channel_id: int,
#     record_id: int,
#     master_id: int,
#     date: str,
#     time: str,
#     comment: Optional[str] = "Автоперенос ботом через API",
#     endpoint_url: Optional[str] = None,
#     timeout: float = CRM_HTTP_TIMEOUT_S,
# ) -> Dict[str, Any]:
#     """Перенос услуги пользователя на другую дату и время."""
#     if endpoint_url is None:
#         endpoint_url = f"{CRM_BASE_URL}/appointments/client/records/reschedule"

#     payload = {
#         "user_companychat": user_companychat,
#         "channel_id": channel_id,
#         "record_id": record_id,
#         "master_id": str(master_id),
#         "date": date,
#         "time": time,
#         "comment": comment,
#     }

#     logger.info("=== crm.crm_reschedule_client_record ===")
#     logger.info("Подготовка переноса услуги payload=%s", payload)

#     try:
#         async with httpx.AsyncClient(timeout=timeout) as client:
#             logger.info("POST %s payload=%s", endpoint_url, payload)
#             response = await client.post(endpoint_url, json=payload)
#             response.raise_for_status()
#             resp_json = response.json()
#             logger.info("Перенос услуги успешно выполнен payload=%s", payload)
#             return resp_json

#     except httpx.TimeoutException as e:
#         logger.error("Таймаут при переносе payload=%s: %s", payload, e)
#         raise

#     except httpx.HTTPStatusError as e:
#         status = e.response.status_code
#         body = e.response.text

#         # 5xx лучше ретраить (поднять исключение наверх, чтобы tenacity повторил)
#         if 500 <= status <= 599:
#             logger.error("CRM 5xx (%d). Будет повтор. payload=%s body=%s", status, payload, body)
#             raise

#         logger.error("CRM 4xx (%d). payload=%s body=%s", status, payload, body)
#         return {"success": False, "error": f"HTTP ошибка: {status}", "details": body}

#     except httpx.RequestError as e:
#         # на всякий — сетевое, ретраится tenacity
#         logger.error("Сетевая ошибка при переносе payload=%s: %s", payload, e)
#         raise

#     except Exception as e:
#         logger.exception("Неожиданная ошибка при переносе payload=%s: %s", payload, e)
#         return {"success": False, "error": "Неизвестная ошибка при записи"}
