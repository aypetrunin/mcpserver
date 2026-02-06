"""Переносит запись клиента на другую дату и время через CRM."""

from __future__ import annotations

import logging
from typing import Any, TypedDict, cast

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url


logger = logging.getLogger(__name__.split(".")[-1])

RESCHEDULE_PATH = "/appointments/client/records/reschedule"


class RescheduleClientRecordPayload(TypedDict):
    """Описывает payload переноса записи."""

    user_companychat: int
    channel_id: int
    record_id: int
    master_id: str
    date: str
    time: str
    comment: str | None


class RescheduleClientRecordResponse(TypedDict, total=False):
    """Описывает ответ переноса записи."""

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
    comment: str | None = "Автоперенос ботом через API",
    endpoint_url: str | None = None,
    timeout: float = 0.0,
) -> RescheduleClientRecordResponse:
    """Переносит запись клиента."""
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

    logger.info("Подготовка переноса записи payload=%s", payload)

    try:
        resp_json = await _reschedule_payload(url=url, payload=payload, timeout_s=effective_timeout)
        logger.info("Перенос записи успешно выполнен payload=%s", payload)
        return cast(RescheduleClientRecordResponse, resp_json)

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        body = e.response.text

        logger.error("CRM HTTP %d payload=%s body=%s", status, payload, body[:800])
        return {"success": False, "error": f"HTTP ошибка: {status}", "details": body[:800]}

    except httpx.RequestError as e:
        logger.error("Сетевая ошибка при переносе payload=%s: %s", payload, e)
        return {"success": False, "error": "network_error", "details": str(e)[:800]}

    except ValueError as e:
        logger.error("Некорректный ответ CRM при переносе payload=%s: %s", payload, e)
        return {"success": False, "error": "invalid_response", "details": str(e)[:800]}

    except Exception as e:
        logger.exception("Неожиданная ошибка при переносе payload=%s: %s", payload, e)
        return {"success": False, "error": "unknown_error"}


@CRM_HTTP_RETRY
async def _reschedule_payload(*, url: str, payload: RescheduleClientRecordPayload, timeout_s: float) -> dict[str, Any]:
    """Выполняет HTTP-запрос переноса и возвращает JSON."""
    client = get_http()

    resp = await client.post(
        url,
        json=payload,
        timeout=httpx.Timeout(timeout_s),
    )
    resp.raise_for_status()

    try:
        data = resp.json()
    except Exception as e:
        raise ValueError(f"Недопустимый ответ JSON от CRM: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Неожиданный тип JSON из CRM: {type(data)}")

    return data
