"""Модуль чтения расписания клиента."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal, TypedDict, cast

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from .crm_settings import (
    CRM_BASE_URL,
    CRM_HTTP_TIMEOUT_S,
    CRM_HTTP_RETRIES,
    CRM_RETRY_MIN_DELAY_S,
    CRM_RETRY_MAX_DELAY_S,
)

logger = logging.getLogger(__name__)


class ErrorResponse(TypedDict):
    success: Literal[False]
    error: str


class Lesson(TypedDict, total=False):
    record_id: int | str
    service: str
    date: str
    time: str
    teacher: str


class SuccessResponse(TypedDict):
    success: Literal[True]
    lessons: list[Lesson]


ResponsePayload = ErrorResponse | SuccessResponse


def _log_and_build_input_error(param_name: str, value: Any) -> ErrorResponse:
    logger.warning(
        "Не указан или неверный тип '%s': %r",
        param_name,
        value,
    )
    return ErrorResponse(
        success=False,
        error=(
            "Ошибка в типах входных данных. "
            "Проверь и перезапусти инструмент."
        ),
    )


def _validate_str_param(name: str, value: Any) -> bool:
    return isinstance(value, str) and bool(value)


@retry(
    stop=stop_after_attempt(CRM_HTTP_RETRIES),
    wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def go_get_client_lessons(
    phone: str,
    channel_id: str,
    timeout: float = CRM_HTTP_TIMEOUT_S,
) -> ResponsePayload:
    """Получение расписания клиента."""

    logger.info("===crm_go.get_client_lessons===")

    for name, value in (("channel_id", channel_id), ("phone", phone)):
        if not _validate_str_param(name, value):
            return _log_and_build_input_error(name, value)

    url = f"{CRM_BASE_URL}/appointments/go_crm/get_records"

    payload: dict[str, str] = {
        "channel_id": channel_id,
        "phone": phone,
    }

    logger.info("Отправка запроса на %s с payload=%r", url, payload)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url=url, json=payload)
            response.raise_for_status()
            resp_json: dict[str, Any] = response.json()

    except (httpx.TimeoutException, httpx.ConnectError) as e:
        msg = f"Сетевая ошибка при доступе к серверу {url} с payload={payload!r}: {e}"
        logger.exception(msg)
        return ErrorResponse(success=False, error=msg)
    
    except httpx.HTTPError as e:
        msg = f"HTTP-ошибка при доступе к серверу {url} с payload={payload!r}: {e}"
        logger.exception(msg)
        return ErrorResponse(success=False, error=msg)
    
    except Exception as e:  # noqa: BLE001
        msg = f"Неожиданная ошибка при доступе к серверу {url} с payload={payload!r}: {e}"
        logger.exception(msg)
        return ErrorResponse(success=False, error=msg)

    if not bool(resp_json.get("success")):
        msg = f"Нет данных в системе для channel_id={channel_id}, phone={phone}"
        logger.warning(msg)
        return ErrorResponse(success=False, error=msg)

    lessons_raw = resp_json.get("lessons") or []
    lessons_list = cast(list[dict[str, Any]], lessons_raw)

    required_keys = ["record_id", "service", "date", "time", "teacher"]

    filtered_lessons: list[Lesson] = []
    for lesson in lessons_list:
        filtered_lesson: Lesson = {}
        for key in required_keys:
            if key in lesson:
                filtered_lesson[key] = lesson[key]
        filtered_lessons.append(filtered_lesson)

    return SuccessResponse(
        success=True,
        lessons=filtered_lessons,
    )


# # Пример использования
# if __name__ == "__main__":
#     """Тестовый пример работы функции."""

#     async def main()->None:
#         """Тестовый пример работы функции."""
#         phone = "89131052808"
#         channel_id = "20"
#         logger.info("Расписание уроков:")
#         results = await go_get_client_lessons(phone=phone, channel_id=channel_id)
#         for result in results:
#             logger.info(result)

#     asyncio.run(main())

# # cd /home/copilot_superuser/petrunin/zena/mcpserver
# # uv run python -m src.crm.crm_current_client_records