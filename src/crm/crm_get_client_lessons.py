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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[logging.StreamHandler()],
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


BASE_URL: str = "https://httpservice.ai2b.pro"
TIMEOUT_SECONDS: float = 180.0
MAX_RETRIES: int = 3


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def go_get_client_lessons(
    phone: str,
    channel_id: str,
    timeout: float = TIMEOUT_SECONDS,
) -> ResponsePayload:
    """Получение расписания клиента."""

    logger.info("===crm_go.get_client_lessons===")

    for name, value in (("channel_id", channel_id), ("phone", phone)):
        if not _validate_str_param(name, value):
            return _log_and_build_input_error(name, value)

    url = f"{BASE_URL}/appointments/go_crm/get_records"

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
        return  ErrorResponse(success=False, error=msg)

    if not bool(resp_json.get("success")):
        msg = f"Нет данных в системе для channel_id={channel_id}, phone={phone}",
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







# import asyncio
# import logging
# import httpx

# from typing import Any, TypedDict, cast


# from tenacity import (
#     retry,
#     retry_if_exception_type,
#     stop_after_attempt,
#     wait_exponential,
# )

# # Настройка логгера
# # ✅ НАСТРОЙКА ЛОГГИРОВАНЩИКА
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s]: %(message)s',
#     handlers=[logging.StreamHandler()]
# )
# logger = logging.getLogger(__name__)


# class Lesson(TypedDict, total=False):
#     record_id: Any
#     service: Any
#     date: Any
#     time: Any
#     teacher: Any


# class GetClientLessonsError(TypedDict):
#     success: bool
#     error: str


# # Константы (лучше вынести в .env или config)
# BASE_URL = "https://httpservice.ai2b.pro"
# TIMEOUT_SECONDS = 180.0
# MAX_RETRIES = 3


# @retry(
#     stop=stop_after_attempt(MAX_RETRIES),
#     wait=wait_exponential(multiplier=1, min=1, max=10),
#     retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
#     reraise=True,
# )
# async def go_get_client_lessons(
#     phone: str,
#     channel_id: str,
#     timeout: float = TIMEOUT_SECONDS,
# ) -> list[dict[str, Any]]:
#     """Функция получения расписания клиента."""

#     logger.info("===crm_go.get_client_lessons===")

#     if not channel_id or not isinstance(channel_id, str):
#         logger.warning(
#             "Не указан или не правильный тип 'channel_id': %s",
#             channel_id,
#         )
#         return [
#             {
#                 "success": False,
#                 "error": (
#                     "Ошибка в типах входных данных. "
#                     "Проверь и перезапусти инструмент."
#                 ),
#             }
#         ]

#     if not phone or not isinstance(phone, str):
#         logger.warning(
#             "Не указан или не правильный тип 'phone': %s",
#             phone,
#         )
#         return [
#             {
#                 "success": False,
#                 "error": (
#                     "Ошибка в типах входных данных. "
#                     "Проверь и перезапусти инструмент."
#                 ),
#             }
#         ]

#     try:
#         async with httpx.AsyncClient(timeout=timeout) as client:
#             request_url = f"{BASE_URL}/appointments/go_crm/get_records"
#             logger.info(
#                 "Отправка запроса на %s с channel_id=%s, phone=%s",
#                 request_url,
#                 channel_id,
#                 phone,
#             )

#             response = await client.post(
#                 url=request_url,
#                 json={
#                     "channel_id": channel_id,
#                     "phone": phone,
#                 },
#             )
#             response.raise_for_status()

#             resp_json_raw = response.json()
#             resp_json = cast(dict[str, Any], resp_json_raw)

#             if not resp_json.get("success"):
#                 logger.warning(
#                     "API вернуло success=False для channel_id=%s, phone=%s",
#                     channel_id,
#                     phone,
#                 )
#                 return [
#                     {
#                         "success": False,
#                         "error": (
#                             "Нет данных в системе для channel_id=%s, phone=%s",
#                             channel_id,
#                             phone,
#                         ),
#                     }
#                 ]

#             lessons_raw = resp_json.get("lessons") or []
#             lessons = cast(list[dict[str, Any]], lessons_raw)

#             required_keys = ["record_id", "service", "date", "time", "teacher"]

#             filtered_lessons: list[Lesson] = []
#             for lesson in lessons:
#                 filtered_lesson: Lesson = {
#                     key: lesson.get(key) for key in required_keys
#                 }
#                 filtered_lessons.append(filtered_lesson)

#             return cast(list[dict[str, Any]], filtered_lessons)

#     except Exception as exc:
#         logger.exception(
#             "Ошибка доступа к серверу с channel_id=%s, phone=%s: %s",
#             channel_id,
#             phone,
#             exc,
#         )
#         error_result: GetClientLessonsError = {
#             "success": False,
#             "error": "Нет доступа к серверу с данными.",
#         }
#         return [cast(dict[str, Any], error_result)]



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