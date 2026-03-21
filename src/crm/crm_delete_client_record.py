"""Удаление записи клиента в CRM.

URL и настройки читаются лениво при выполнении запроса, а не при импорте модуля.

Правило:
- success=True означает, что на стороне CRM не было ошибок.
- success=False означает, что CRM вернула ошибку (бизнес/валидация/прочее).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from typing_extensions import TypedDict

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url
from ._crm_result import Payload, err, ok


logger = logging.getLogger(__name__.split(".")[-1])

DELETE_RECORDS_PATH = "/appointments/client/records/delete"


class DeleteClientRecordPayload(TypedDict):
    """Payload для удаления записи."""

    user_companychat: int
    channel_id: int
    record_id: int


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


async def delete_client_record(
    user_companychat: int,
    office_id: int,
    record_id: int,
) -> Payload[str]:
    """Удаляет запись клиента.

    Возвращает:
    - ok("...") если CRM отработала без ошибок (success=True)
    - err(code,error) если CRM/сеть/ответ сломан
    """
    payload: DeleteClientRecordPayload = {
        "user_companychat": user_companychat,
        "channel_id": office_id,
        "record_id": record_id,
    }

    try:
        resp_json = await _delete_client_record_payload(payload)

        # Что делаем:
        # - success=True => CRM ошибок не было => ok(...)
        # - success=False => CRM вернула ошибку => err(crm_error,...)
        if resp_json.get("success") is True:
            return ok(f"Запись удалена (office_id={office_id}, record_id={record_id}).")

        # Если CRM в ответе даёт текст ошибки/сообщение — можно аккуратно использовать.
        # Но наружу по контракту: code + человекочитаемая error.
        msg = resp_json.get("error") or resp_json.get("message") or ""
        msg_str = msg if isinstance(msg, str) else ""

        return err(
            code="crm_error",
            error=msg_str or "CRM не смогла удалить запись",
        )

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        logger.warning(
            "crm_delete_client_record http error status=%s body=%s",
            status,
            (e.response.text or "")[:500],
        )
        return err(code=_code_from_status(status), error=f"HTTP {status} from CRM")

    except httpx.RequestError as e:
        logger.warning("crm_delete_client_record request error: %s", e)
        return err(code="network_error", error="Network error while calling CRM")

    except ValueError as e:
        # Что делаем:
        # ValueError используем только для плохого JSON/не того типа ответа
        logger.error("crm_delete_client_record bad response payload=%s: %s", payload, e)
        return err(code="invalid_response", error="Invalid response from CRM")

    except Exception as e:
        logger.exception(
            "crm_delete_client_record unexpected error payload=%s: %s", payload, e
        )
        return err(code="internal_error", error="Unexpected error")


@CRM_HTTP_RETRY
async def _delete_client_record_payload(
    payload: DeleteClientRecordPayload,
) -> dict[str, Any]:
    """HTTP-запрос удаления записи, возвращает JSON dict."""
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
