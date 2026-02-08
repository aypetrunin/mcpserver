# crm_get_client_records.py
"""Поиск записей клиента в CRM.

URL и настройки вычисляются лениво при выполнении запроса, а не при импорте.

Правило:
- success=True означает, что на стороне CRM не было ошибок
- отсутствие записей НЕ является ошибкой (ok([]) — нормальный результат)
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

import httpx
from typing_extensions import TypedDict

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url
from ._crm_result import Payload, err, ok


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


class ClientRecordsPayload(TypedDict):
    """Описывает payload запроса записей."""

    user_companychat: int
    channel_id: int


def _code_from_status(status: int) -> str:
    if status in (401, 403):
        return "unauthorized"
    if status == 404:
        return "not_found"
    if status == 409:
        return "conflict"
    if status == 422:
        return "validation_error"
    if status == 429:
        return "rate_limited"
    if 500 <= status <= 599:
        return "crm_unavailable"
    return "crm_error"


async def get_client_records(
    user_companychat: int, channel_id: int
) -> Payload[list[PersonalRecord]]:
    """Возвращает записи клиента из CRM (единый контракт)."""
    payload: ClientRecordsPayload = {
        "user_companychat": user_companychat,
        "channel_id": channel_id,
    }

    try:
        resp_json = await _fetch_client_records_payload(payload)

        crm_ok, records = _extract_records(resp_json, channel_id)

        # success=True => CRM без ошибок; записей может не быть -> ok([])
        if crm_ok:
            return ok(records)

        # success=False => CRM сообщает об ошибке (не invalid_response)
        return err(code="crm_error", error="CRM error while fetching client records")

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        logger.warning(
            "http error status=%s body=%s",
            status,
            (e.response.text or "")[:500],
        )
        return err(code=_code_from_status(status), error=f"HTTP {status} from CRM")

    except httpx.RequestError as e:
        logger.warning("request error: %s", e)
        return err(code="network_error", error="Network error while calling CRM")

    except ValueError as e:
        # ValueError — это про парсинг/валидацию ответа CRM (битый JSON/тип)
        logger.error("bad response payload=%s: %s", payload, e)
        return err(code="invalid_response", error="Invalid response from CRM")

    except Exception as e:
        logger.exception("unexpected error payload=%s: %s", payload, e)
        return err(code="internal_error", error="Unexpected error")


@CRM_HTTP_RETRY
async def _fetch_client_records_payload(
    payload: ClientRecordsPayload,
) -> dict[str, Any]:
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


def _extract_records(
    response: dict[str, Any], channel_id: int
) -> tuple[bool, list[PersonalRecord]]:
    """Извлекает и нормализует записи из ответа CRM.

    Возвращает:
      - (True, records) если CRM success=True (ошибок не было), records может быть пустым
      - (False, [])     если CRM success=False (CRM сообщила об ошибке)
    """
    if response.get("success") is not True:
        return False, []

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
    return True, result
