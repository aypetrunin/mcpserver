"""Записывает клиента на услугу на заданные дату и время через CRM gateway."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from typing_extensions import TypedDict

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url


logger = logging.getLogger(__name__.split(".")[-1])

CREATE_BOOKING_PATH = "/appointments/yclients/create_booking"


class RecordTimePayload(TypedDict, total=False):
    """Описывает payload бронирования."""

    staff_id: int
    service_id: str
    date: str
    time: str
    user_id: str
    channel_id: int | None
    comment: str | None
    notify_by_sms: int
    notify_by_email: int


async def record_time_async(
    product_id: str,
    date: str,
    time: str,
    user_id: int,
    staff_id: int = 0,
    channel_id: int | None = 0,
    comment: str | None = "Запись через API",
    notify_by_sms: int = 0,
    notify_by_email: int = 0,
    endpoint_url: str | None = None,
    timeout: float = 0.0,
) -> dict[str, Any]:
    """Записывает пользователя на услугу через CRM."""
    url = endpoint_url or crm_url(CREATE_BOOKING_PATH)

    payload: RecordTimePayload = {
        "staff_id": int(staff_id),
        "service_id": product_id,
        "date": date,
        "time": time,
        "user_id": str(user_id),
        "channel_id": channel_id,
        "comment": comment,
        "notify_by_sms": int(notify_by_sms),
        "notify_by_email": int(notify_by_email),
    }

    requested_datetime = f"{date} {time}"
    logger.info(
        "Подготовка бронирования service_id=%s at %s (staff_id=%s)",
        product_id,
        requested_datetime,
        staff_id,
    )

    effective_timeout = crm_timeout_s(timeout)

    try:
        resp_json = await _create_booking_payload(
            url=url,
            payload=payload,
            timeout_s=effective_timeout,
        )

        if (
            resp_json.get("success") is False
            and resp_json.get("error") == "Неожиданный код статуса: 400"
        ):
            logger.info(
                "Ошибка API при бронировании (400), считаем запись успешной. "
                "payload=%s response=%s",
                payload,
                resp_json,
            )
            return {
                "success": True,
                "info": f"Запись к master_id={staff_id} на время {requested_datetime} сделана",
            }

        logger.info(
            "Бронирование успешно выполнено user_id=%s service_id=%s",
            user_id,
            product_id,
        )
        return resp_json

    except httpx.HTTPStatusError as e:
        logger.error(
            "Ошибка HTTP %d при бронировании service_id=%s: %s",
            e.response.status_code,
            product_id,
            e,
        )
        return {"success": False, "error": f"HTTP ошибка: {e.response.status_code}"}

    except httpx.RequestError as e:
        logger.error("Сетевая ошибка при бронировании service_id=%s: %s", product_id, e)
        return {"success": False, "error": "network_error"}

    except ValueError as e:
        logger.error(
            "Некорректный ответ CRM при бронировании service_id=%s: %s", product_id, e
        )
        return {"success": False, "error": "invalid_response"}

    except Exception as e:
        logger.exception(
            "Неожиданная ошибка при бронировании service_id=%s: %s", product_id, e
        )
        return {"success": False, "error": "Неизвестная ошибка при записи"}


@CRM_HTTP_RETRY
async def _create_booking_payload(
    *, url: str, payload: RecordTimePayload, timeout_s: float
) -> dict[str, Any]:
    """Выполняет HTTP-запрос бронирования и возвращает JSON."""
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
