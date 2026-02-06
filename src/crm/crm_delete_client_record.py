"""Удаление записи клиента в CRM.

URL и настройки читаются лениво при выполнении запроса, а не при импорте модуля.
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url


logger = logging.getLogger(__name__.split(".")[-1])

DELETE_RECORDS_PATH = "/appointments/client/records/delete"


class DeleteClientRecordPayload(TypedDict):
    """Описывает payload для удаления записи."""

    user_companychat: int
    channel_id: int
    record_id: int


class DeleteClientRecordResponse(TypedDict):
    """Описывает стандартный ответ операции удаления."""

    success: bool
    data: str
    error: str | None


async def delete_client_record(
    user_companychat: int,
    office_id: int,
    record_id: int,
) -> DeleteClientRecordResponse:
    """Удаляет запись клиента."""
    payload: DeleteClientRecordPayload = {
        "user_companychat": user_companychat,
        "channel_id": office_id,
        "record_id": record_id,
    }

    try:
        resp_json = await _delete_client_record_payload(payload)

        if resp_json.get("success") is True:
            return {
                "success": True,
                "data": f"Запись payload={payload} - удалена",
                "error": None,
            }
        return {
            "success": False,
            "data": f"Запись payload={payload} - не существует",
            "error": None,
        }

    except httpx.HTTPStatusError as e:
        logger.warning(
            "crm_delete_client_record http error status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return {"success": False, "data": "", "error": f"status={e.response.status_code}"}

    except httpx.RequestError as e:
        logger.warning("crm_delete_client_record request error: %s", e)
        return {"success": False, "data": "", "error": "network_error"}

    except ValueError as e:
        logger.error("crm_delete_client_record bad response payload=%s: %s", payload, e)
        return {"success": False, "data": "", "error": "invalid_response"}

    except Exception as e:
        logger.exception("crm_delete_client_record unexpected error payload=%s: %s", payload, e)
        return {"success": False, "data": "", "error": "unexpected_error"}


@CRM_HTTP_RETRY
async def _delete_client_record_payload(payload: DeleteClientRecordPayload) -> dict[str, Any]:
    """Выполняет HTTP-запрос удаления записи и возвращает JSON."""
    client = get_http()
    url = crm_url(DELETE_RECORDS_PATH)
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
