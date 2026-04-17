"""Читает расписание клиента из GO CRM.

URL и настройки вычисляются лениво при выполнении запроса, а не при импорте.
"""

from __future__ import annotations

from typing import Any, Literal, cast

import httpx
from typing_extensions import TypedDict

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ..zena_logging import get_logger
from ._crm_http import crm_timeout_s, crm_url


logger = get_logger()

GET_RECORDS_PATH = "/appointments/go_crm/get_records"


class ErrorResponse(TypedDict):
    """Описывает ответ с ошибкой."""

    success: Literal[False]
    error: str


class Lesson(TypedDict, total=False):
    """Описывает урок в расписании."""

    record_id: int | str
    service: str
    date: str
    time: str
    teacher: str


class SuccessResponse(TypedDict):
    """Описывает успешный ответ."""

    success: Literal[True]
    lessons: list[Lesson]


ResponsePayload = ErrorResponse | SuccessResponse


def _log_and_build_input_error(param_name: str, value: Any) -> ErrorResponse:
    """Логирует и возвращает ошибку валидации входных данных."""
    logger.warning("validation_error", param=param_name, value=value)
    return ErrorResponse(
        success=False,
        error="Ошибка в типах входных данных. Проверь и перезапусти инструмент.",
    )


def _validate_str_param(value: Any) -> bool:
    """Проверяет, что значение является непустой строкой."""
    return isinstance(value, str) and bool(value.strip())


@CRM_HTTP_RETRY
async def _fetch_client_lessons(
    payload: dict[str, Any], timeout_s: float
) -> dict[str, Any]:
    """Выполняет запрос к GO CRM и возвращает JSON."""
    client = get_http()
    url = crm_url(GET_RECORDS_PATH)

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


async def go_get_client_lessons(
    phone: str, channel_id: str, timeout: float = 0.0
) -> ResponsePayload:
    """Возвращает расписание клиента из GO CRM."""
    for name, value in (("channel_id", channel_id), ("phone", phone)):
        if not _validate_str_param(value):
            return _log_and_build_input_error(name, value)

    payload: dict[str, str] = {
        "channel_id": channel_id.strip(),
        "phone": phone.strip(),
    }
    effective_timeout = crm_timeout_s(timeout)

    try:
        resp_json = await _fetch_client_lessons(
            payload=payload, timeout_s=effective_timeout
        )

    except httpx.HTTPStatusError as e:
        logger.warning(
            "crm.http_error",
            operation="get_client_lessons",
            status=e.response.status_code,
            body=e.response.text[:500],
        )
        return ErrorResponse(
            success=False,
            error="GO CRM временно недоступен. Обратитесь к администратору.",
        )

    except httpx.RequestError as e:
        logger.warning(
            "crm.request_error",
            operation="get_client_lessons",
            payload=payload,
            error=str(e),
        )
        return ErrorResponse(
            success=False, error="Сетевая ошибка при обращении к GO CRM."
        )

    except ValueError:
        logger.exception(
            "crm.invalid_json",
            operation="get_client_lessons",
            payload=payload,
        )
        return ErrorResponse(success=False, error="GO CRM вернул некорректный ответ.")

    except Exception as e:
        logger.exception(
            "crm.unexpected_error",
            operation="get_client_lessons",
            payload=payload,
            error=str(e),
        )
        return ErrorResponse(
            success=False, error="Неизвестная ошибка при обращении к GO CRM."
        )

    if resp_json.get("success") is not True:
        logger.warning(
            "crm.no_data",
            operation="get_client_lessons",
            channel_id=channel_id,
            phone=phone,
        )
        msg = f"Нет данных в системе для channel_id={channel_id}, phone={phone}"
        return ErrorResponse(success=False, error=msg)

    lessons_raw = resp_json.get("lessons") or []
    if not isinstance(lessons_raw, list):
        return ErrorResponse(
            success=False, error="GO CRM вернул некорректный список уроков."
        )

    lessons_list = cast(list[dict[str, Any]], lessons_raw)

    required_keys = ["record_id", "service", "date", "time", "teacher"]

    filtered_lessons: list[Lesson] = []
    for lesson in lessons_list:
        if not isinstance(lesson, dict):
            continue
        filtered_lesson: Lesson = {}
        for key in required_keys:
            if key in lesson:
                filtered_lesson[key] = lesson[key]
        filtered_lessons.append(filtered_lesson)

    return SuccessResponse(success=True, lessons=filtered_lessons)
