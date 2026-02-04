"""Модуль записи на услугу на определенную дату и время.

Поиск ведется через API CRM gateway (CRM_BASE_URL).
"""

# src/crm/crm_record_time.py
from __future__ import annotations

import logging
from typing import Any, TypedDict

import httpx

from src.clients import get_http
from src.settings import get_settings
from src.http_retry import CRM_HTTP_RETRY

logger = logging.getLogger(__name__)

S = get_settings()

CREATE_BOOKING_PATH = "/appointments/yclients/create_booking"
URL_CREATE_BOOKING = f"{S.CRM_BASE_URL.rstrip('/')}{CREATE_BOOKING_PATH}"


class RecordTimePayload(TypedDict, total=False):
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
    endpoint_url: str = URL_CREATE_BOOKING,
    timeout: float = 0.0,
) -> dict[str, Any]:
    """
    Асинхронная запись пользователя на услугу через API.

    Сигнатуру оставляем максимально близкой к текущей (чтобы не менять вызовы по проекту).
    endpoint_url можно переопределить снаружи.
    timeout если 0/не задан — используем S.CRM_HTTP_TIMEOUT_S.
    """

    logger.info("=== crm.crm_record_time_async ===")

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

    effective_timeout = timeout or float(S.CRM_HTTP_TIMEOUT_S)

    try:
        resp_json = await _create_booking_payload(
            url=endpoint_url,
            payload=payload,
            timeout_s=effective_timeout,
        )

        # 🔥 Обработка бага API (как в текущем коде):
        # иногда API возвращает success=False и error="Неожиданный код статуса: 400",
        # но по факту запись создана — считаем успехом.
        if (
            isinstance(resp_json, dict)
            and resp_json.get("success") is False
            and resp_json.get("error") == "Неожиданный код статуса: 400"
        ):
            logger.info(
                "Обнаружена ошибка API при бронировании (400), считаем запись успешной. "
                "Payload=%s, Response=%s",
                payload,
                resp_json,
            )
            return {
                "success": True,
                "info": f"Запись к master_id={staff_id} на время {requested_datetime} сделана",
            }

        logger.info("Бронирование успешно выполнено user_id=%s, service_id=%s", user_id, product_id)
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
        # сетевые ошибки сюда попадут, если retry исчерпан
        logger.error("Сетевая ошибка при бронировании service_id=%s: %s", product_id, e)
        return {"success": False, "error": "network_error"}

    except ValueError as e:
        logger.error("Некорректный ответ CRM при бронировании service_id=%s: %s", product_id, e)
        return {"success": False, "error": "invalid_response"}

    except Exception as e:  # noqa: BLE001
        logger.exception("Неожиданная ошибка при бронировании service_id=%s: %s", product_id, e)
        return {"success": False, "error": "Неизвестная ошибка при записи"}


@CRM_HTTP_RETRY
async def _create_booking_payload(
    *,
    url: str,
    payload: RecordTimePayload,
    timeout_s: float,
) -> dict[str, Any]:
    """
    Низкоуровневый HTTP-вызов с единым retry-поведением:
    - timeout / network error
    - HTTP 429
    - HTTP 5xx
    """
    client = get_http()

    logger.info("POST %s payload=%s", url, payload)
    resp = await client.post(
        url,
        json=payload,
        timeout=httpx.Timeout(timeout_s),
    )
    resp.raise_for_status()

    try:
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Недопустимый ответ JSON от CRM: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Неожиданный тип JSON из CRM: {type(data)}")

    return data



# import asyncio
# import logging
# from typing import Any, Dict

# import httpx
# from tenacity import (
#     retry,
#     retry_if_exception_type,
#     stop_after_attempt,
#     wait_exponential,
# )
# from .crm_settings import (
#     CRM_BASE_URL,
#     CRM_HTTP_TIMEOUT_S,
#     CRM_HTTP_RETRIES,
#     CRM_RETRY_MIN_DELAY_S,
#     CRM_RETRY_MAX_DELAY_S,
# )


# from .crm_avaliable_time_for_master import avaliable_time_for_master_async

# # Настройка логгера
# logger = logging.getLogger(__name__)

# @retry(
#     stop=stop_after_attempt(CRM_HTTP_RETRIES),
#     wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
#     retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
#     reraise=True,
# )
# async def record_time_async(
#     product_id: str,
#     date: str,
#     time: str,
#     user_id: int,
#     staff_id: int = 0,
#     channel_id: int | None = 0,
#     comment: str | None = "Запись через API",
#     notify_by_sms: int = 0,
#     notify_by_email: int = 0,
#     endpoint_url: str = f"{CRM_BASE_URL}/appointments/yclients/create_booking",
#     timeout: float = CRM_HTTP_TIMEOUT_S,
# ) -> Dict[str, Any]:
#     """Асинхронная запись пользователя на услугу через API с предварительной проверкой слотов.

#     :param product_id: ID услуги (service_id)
#     :param date: Дата в формате YYYY-MM-DD
#     :param time: Время в формате HH:MM
#     :param user_id: ID пользователя в локальной БД
#     :param staff_id: ID сотрудника (0, если не требуется)
#     :param channel_id: ID канала (опционально)
#     :param comment: Комментарий
#     :param notify_by_sms: Уведомлять по SMS (0 или 1)
#     :param notify_by_email: Уведомлять по Email (0 или 1)
#     :param endpoint_url: Полный URL API (по умолчанию BASE_URL/create_booking)
#     :param timeout: Таймаут запроса в секундах
#     :return: dict — ответ сервера или сообщение об ошибке
#     """
#     payload = {
#         "staff_id": int(staff_id),
#         "service_id": product_id,
#         "date": date,
#         "time": time,
#         "user_id": str(user_id),
#         "channel_id": channel_id,
#         "comment": comment,
#         "notify_by_sms": notify_by_sms,
#         "notify_by_email": notify_by_email,
#     }
#     logger.info("===record_time_async===")
#     requested_datetime = f"{date} {time}"
#     logger.info(
#         "Подготовка бронирования для  service_id=%s at %s (staff_id=%s)",
#         product_id,
#         requested_datetime,
#         staff_id,
#     )
#     logger.info("Проверка доступности времени - НЕТ")

#     # Отправка запроса на запись
#     try:
#         async with httpx.AsyncClient(timeout=timeout) as client:
#             logger.info(
#                 "Отправка запроса на бронирование %s with payload=%s", endpoint_url, payload
#             )
#             response = await client.post(endpoint_url, json=payload)
#             response.raise_for_status()
#             resp_json = response.json()

#             # 🔥 Обработка бага API (этап записи)
#             if (
#                 isinstance(resp_json, dict)
#                 and resp_json.get("success") is False
#                 and resp_json.get("error") == "Неожиданный код статуса: 400"
#             ):
#                 logger.info(
#                     "Обнаружена ошибка API при бронировании (400). Бронирование считается успешным. "
#                     "Payload=%s, Response=%s",
#                     payload,
#                     resp_json,
#                 )
#                 return {
#                     "success": True,
#                     "info": f"Запись к master_id={staff_id} на время {requested_datetime} сделана",
#                 }

#             logger.info(
#                 "Бронирование успешно выполнено для user_id=%s, service_id=%s", user_id, product_id
#             )
#             return resp_json

#     except httpx.TimeoutException as e:
#         logger.error("Таймаут при бронировании service_id=%s: %s", product_id, e)
#         raise  # повторная попытка через tenacity

#     except httpx.HTTPStatusError as e:
#         logger.error(
#             "Ошибка HTTP %d при бронировании service_id=%s: %s",
#             e.response.status_code,
#             product_id,
#             e,
#         )
#         return {"success": False, "error": f"HTTP ошибка: {e.response.status_code}"}

#     except Exception as e:
#         logger.exception(
#             "Неожиданная ошибка при бронировании service_id=%s: %s", product_id, e
#         )
#         return {"success": False, "error": "Неизвестная ошибка при записи"}


# # Пример использования
# if __name__ == "__main__":
#     """Тестовый пример работы функции."""

#     async def main() -> None:
#         """Тестовый пример работы функции."""
#         url = f"{CRM_BASE_URL}/appointments/yclients/create_booking"  # или твой боевой URL
#         result = await record_time_async(
#             endpoint_url=url,
#             staff_id=4131055,
#             product_id="1-11620650",
#             date="2025-10-22",
#             time="13:00",
#             user_id=1176612320,  # ID пользователя в твоей БД
#             channel_id=0,  # ID канала
#             comment="Запись через API",
#             notify_by_sms=1,
#             notify_by_email=1,
#         )
#         logger.info(result)

#     asyncio.run(main())

# # cd /home/copilot_superuser/petrunin/mcp/zena_qdrant
# # python -m zena_qdrant.yclients.record_time
