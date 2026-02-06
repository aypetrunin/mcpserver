"""Поиск записей клиента в CRM.

URL и настройки вычисляются лениво при выполнении запроса, а не при импорте.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, TypedDict

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url


logger = logging.getLogger(__name__.split(".")[-1])

CLIENT_RECORDS_PATH = "/appointments/client/records"


class PersonalRecord(TypedDict, total=False):
    """Описывает запись клиента."""

    record_id: int
    record_date: str
    office_id: int
    master_id: int
    master_name: str
    product_id: str
    product_name: str


class PersonalRecordsResponse(TypedDict):
    """Описывает формат ответа поиска записей."""

    success: bool
    data: list[PersonalRecord]
    error: str | None


class ClientRecordsPayload(TypedDict):
    """Описывает payload запроса записей."""

    user_companychat: int
    channel_id: int


async def get_client_records(user_companychat: int, channel_id: int) -> PersonalRecordsResponse:
    """Возвращает записи клиента из CRM."""
    payload: ClientRecordsPayload = {
        "user_companychat": user_companychat,
        "channel_id": channel_id,
    }

    try:
        resp_json = await _fetch_client_records_payload(payload)
        return _response_format(resp_json, channel_id)

    except httpx.HTTPStatusError as e:
        logger.warning(
            "http error status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return {"success": False, "data": [], "error": f"status={e.response.status_code}"}

    except httpx.RequestError as e:
        logger.warning("request error: %s", e)
        return {"success": False, "data": [], "error": "network_error"}

    except ValueError as e:
        logger.error("bad response payload=%s: %s", payload, e)
        return {"success": False, "data": [], "error": "invalid_response"}

    except Exception as e:
        logger.exception("unexpected error payload=%s: %s", payload, e)
        return {"success": False, "data": [], "error": "unexpected_error"}


@CRM_HTTP_RETRY
async def _fetch_client_records_payload(payload: ClientRecordsPayload) -> dict[str, Any]:
    """Выполняет HTTP-запрос поиска записей и возвращает JSON."""
    client = get_http()
    url = crm_url(CLIENT_RECORDS_PATH)
    timeout_s = crm_timeout_s(0.0)

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


def _parse_dt(dt_str: str) -> datetime | None:
    """Пытается распарсить дату из строки."""
    if not dt_str:
        return None

    for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%d.%m.%y %H:%M"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def _response_format(response: dict[str, Any], channel_id: int) -> PersonalRecordsResponse:
    """Приводит ответ CRM к формату проекта."""
    if response.get("success") is not True:
        return {"success": False, "data": [], "error": "Ошибка поиска записей клиента"}

    result: list[PersonalRecord] = []

    for record in response.get("records", []):
        if not isinstance(record, dict):
            continue

        if record.get("success") is not True:
            continue

        if record.get("status") != "Ожидает...":
            continue

        master = record.get("master_id") or {}
        product = record.get("product") or {}

        rec_date = record.get("date")
        if not rec_date:
            continue

        result.append(
            {
                "record_id": record.get("id"),
                "record_date": str(rec_date),
                "office_id": channel_id,
                "master_id": master.get("id"),
                "master_name": master.get("name"),
                "product_id": f"{channel_id}-{product.get('id')}",
                "product_name": product.get("name"),
            }
        )

    result.sort(key=lambda x: _parse_dt(x.get("record_date", "")) or datetime.max)
    return {"success": True, "data": result, "error": None}
