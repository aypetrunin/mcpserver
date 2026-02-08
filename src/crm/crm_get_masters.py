"""Получает список мастеров из CRM.

URL и настройки вычисляются лениво при выполнении запроса, а не при импорте.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, cast

import httpx
from typing_extensions import TypedDict

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url
from ._crm_result import Payload, err, ok


logger = logging.getLogger(__name__.split(".")[-1])

MASTERS_PATH = "/appointments/yclients/staff/actual"


class Master(TypedDict, total=False):
    """Описывает мастера."""

    id: int
    name: str


class MastersOk(TypedDict):
    """Описывает успешный ответ CRM."""

    success: Literal[True]
    masters: list[Master]


@CRM_HTTP_RETRY
async def _fetch_masters_payload(
    payload: dict[str, Any], timeout_s: float
) -> dict[str, Any]:
    """Выполняет запрос списка мастеров и возвращает JSON."""
    client = get_http()
    url = crm_url(MASTERS_PATH)

    resp = await client.post(
        url,
        json=payload,
        timeout=httpx.Timeout(timeout_s),
    )
    resp.raise_for_status()

    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Неожиданный тип JSON из CRM: {type(data)}")
    return data


async def get_masters(channel_id: int, timeout: float = 0.0) -> Payload[list[Master]]:
    """Возвращает список мастеров для канала."""
    payload = {"channel_id": channel_id}
    effective_timeout = crm_timeout_s(timeout)

    try:
        resp_any = await _fetch_masters_payload(
            payload=payload, timeout_s=effective_timeout
        )

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP %s при получении мастеров channel_id=%s body=%s",
            e.response.status_code,
            channel_id,
            e.response.text[:500],
        )
        return err(code="http_error", error=f"CRM вернул HTTP {e.response.status_code}")

    except httpx.RequestError as e:
        logger.warning(
            "Сетевая ошибка при получении мастеров channel_id=%s: %s",
            channel_id,
            e,
        )
        return err(
            code="network_error", error="Сетевая ошибка при получении списка мастеров"
        )

    except ValueError:
        logger.exception("CRM вернул некорректный JSON channel_id=%s", channel_id)
        return err(code="crm_bad_response", error="CRM вернул некорректный JSON")

    except Exception:
        logger.exception(
            "Неожиданная ошибка при получении мастеров channel_id=%s", channel_id
        )
        return err(
            code="unexpected_error",
            error="Неизвестная ошибка при получении списка мастеров",
        )

    if not isinstance(resp_any, dict):
        return err(code="crm_bad_response", error="CRM вернул некорректный JSON")

    resp = cast(dict[str, Any], resp_any)

    if resp.get("success") is not True:
        return err(code="crm_error", error="CRM вернул ошибку при получении мастеров")

    masters_raw = resp.get("masters")
    if not isinstance(masters_raw, list):
        return err(
            code="crm_bad_response", error="CRM вернул некорректный список мастеров"
        )

    masters: list[Master] = []
    for item in masters_raw:
        if isinstance(item, dict):
            masters.append({"id": item.get("id"), "name": item.get("name")})

    return ok(masters)
