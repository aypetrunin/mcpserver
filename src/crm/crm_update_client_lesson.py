"""Переносит урок клиента в GO CRM на другую дату и время."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Literal, TypedDict

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url
from .crm_get_client_statistics import go_get_client_statisics


logger = logging.getLogger(__name__.split(".")[-1])

RESCHEDULE_PATH = "/appointments/go_crm/reschedule_record"


class ErrorResponse(TypedDict):
    """Описывает ответ с ошибкой."""

    success: Literal[False]
    error: str


class SuccessResponse(TypedDict):
    """Описывает успешный ответ."""

    success: Literal[True]
    message: str


ResponsePayload = ErrorResponse | SuccessResponse


def _log_and_build_input_error(param_name: str, value: Any) -> ErrorResponse:
    """Логирует и возвращает ошибку валидации входных данных."""
    logger.warning("Не указан или неверный тип '%s': %r", param_name, value)
    return ErrorResponse(
        success=False,
        error="Ошибка в типах входных данных. Проверь и перезапусти инструмент.",
    )


def _validate_str_param(value: Any) -> bool:
    """Проверяет, что значение является непустой строкой."""
    return isinstance(value, str) and bool(value.strip())


def normalize_date(value: str | None) -> str | None:
    """Нормализует дату в формат DD.MM.YYYY."""
    if not value:
        return None

    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {value}")


@CRM_HTTP_RETRY
async def _reschedule_record_payload(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    """Выполняет запрос переноса урока и возвращает JSON."""
    client = get_http()
    url = crm_url(RESCHEDULE_PATH)

    resp = await client.post(
        url,
        json=payload,
        timeout=httpx.Timeout(timeout_s),
    )
    resp.raise_for_status()

    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected JSON type from CRM: {type(data)}")
    return data


async def go_update_client_lesson(
    phone: str,
    channel_id: str,
    record_id: str,
    instructor_name: str,
    new_date: str,
    new_time: str,
    service: str,
    reason: str,
    timeout: float = 0.0,
) -> ResponsePayload:
    """Переносит урок клиента в GO CRM."""
    for name, value in (
        ("phone", phone),
        ("channel_id", channel_id),
        ("record_id", record_id),
        ("instructor_name", instructor_name),
        ("new_date", new_date),
        ("new_time", new_time),
        ("service", service),
        ("reason", reason),
    ):
        if not _validate_str_param(value):
            return _log_and_build_input_error(name, value)

    try:
        normalized_new_date = normalize_date(new_date) or new_date
    except ValueError:
        return ErrorResponse(success=False, error=f"Неверный формат даты: {new_date}. Ожидается DD.MM.YYYY")

    statistic = await go_get_client_statisics(phone=phone, channel_id=channel_id)
    abonent_end_date: Any = None
    next_transfer_after: Any = None

    if statistic.get("success") is True:
        msg = statistic.get("message") or {}
        if isinstance(msg, dict):
            abonent_end_date = msg.get("end_date")
            next_transfer_after = msg.get("next_transfer_after")

    try:
        transfer_date = datetime.strptime(normalized_new_date, "%d.%m.%Y")
    except ValueError:
        return ErrorResponse(success=False, error=f"Неверный формат даты: {new_date}. Ожидается DD.MM.YYYY")

    abonent_end_dt = None
    next_transfer_dt = None
    try:
        if abonent_end_date:
            abonent_end_dt = datetime.strptime(str(abonent_end_date), "%d.%m.%Y")
        if next_transfer_after:
            next_transfer_dt = datetime.strptime(str(next_transfer_after), "%d.%m.%Y")
    except ValueError:
        logger.warning(
            "Некорректные даты из статистики: end_date=%r next_transfer_after=%r",
            abonent_end_date,
            next_transfer_after,
        )

    if abonent_end_dt and next_transfer_dt:
        if not (transfer_date <= abonent_end_dt or transfer_date >= next_transfer_dt):
            msg = (
                "В этом месяце после окончания абонемента у Вас уже было 2 переноса. "
                "Вы можете перенести занятие после {}"
            ).format(next_transfer_dt.strftime("%d.%m.%Y"))
            logger.warning("%s", msg)
            return ErrorResponse(success=False, error=msg)

    payload: dict[str, str] = {
        "channel_id": channel_id.strip(),
        "phone": phone.strip(),
        "record_id": record_id.strip(),
        "instructor_name": instructor_name.strip(),
        "new_date": normalized_new_date.strip(),
        "new_time": new_time.strip(),
        "service": service.strip(),
        "reason": reason.strip(),
    }

    effective_timeout = crm_timeout_s(timeout)

    try:
        resp_json = await _reschedule_record_payload(payload=payload, timeout_s=effective_timeout)

    except httpx.HTTPStatusError as e:
        logger.warning(
            "go_update_client_lesson http error status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return ErrorResponse(success=False, error="GO CRM временно недоступен. Обратитесь к администратору.")

    except httpx.RequestError as e:
        logger.warning("go_update_client_lesson request error payload=%s: %s", payload, e)
        return ErrorResponse(success=False, error="Сетевая ошибка при обращении к GO CRM.")

    except ValueError:
        logger.exception("go_update_client_lesson invalid json payload=%s", payload)
        return ErrorResponse(success=False, error="GO CRM вернул некорректный ответ.")

    except Exception as e:
        logger.exception("go_update_client_lesson unexpected error payload=%s: %s", payload, e)
        return ErrorResponse(success=False, error="Неизвестная ошибка при обращении к GO CRM.")

    if resp_json.get("success") is not True:
        return ErrorResponse(success=False, error="Ошибка переноса урока. Обратитесь к администратору.")

    api_new_date = str(resp_json.get("new_date", normalized_new_date))
    api_new_time = str(resp_json.get("new_time", new_time))

    return SuccessResponse(
        success=True,
        message=f"Перенос урока выполнен успешно на {api_new_date} {api_new_time}!",
    )
