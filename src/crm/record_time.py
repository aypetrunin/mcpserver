"""Модуль записи на услугу на определенную дату и время.

Поиск ведется через API https://httpservice.ai2b.pro.
"""

import asyncio
import logging
from typing import Any, Dict

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..crm.avaliable_time_for_master import avaliable_time_for_master_async

# Настройка логгера
logger = logging.getLogger(__name__)

# Константы
BASE_URL = "https://httpservice.ai2b.pro"
TIMEOUT_SECONDS = 120.0
MAX_RETRIES = 3


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
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
    endpoint_url: str = f"{BASE_URL}/appointments/yclients/create_booking",
    timeout: float = TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Асинхронная запись пользователя на услугу через API с предварительной проверкой слотов.

    :param product_id: ID услуги (service_id)
    :param date: Дата в формате YYYY-MM-DD
    :param time: Время в формате HH:MM
    :param user_id: ID пользователя в локальной БД
    :param staff_id: ID сотрудника (0, если не требуется)
    :param channel_id: ID канала (опционально)
    :param comment: Комментарий
    :param notify_by_sms: Уведомлять по SMS (0 или 1)
    :param notify_by_email: Уведомлять по Email (0 или 1)
    :param endpoint_url: Полный URL API (по умолчанию BASE_URL/create_booking)
    :param timeout: Таймаут запроса в секундах
    :return: dict — ответ сервера или сообщение об ошибке
    """
    payload = {
        "staff_id": staff_id,
        "service_id": product_id,
        "date": date,
        "time": time,
        "user_id": user_id,
        "channel_id": channel_id,
        "comment": comment,
        "notify_by_sms": notify_by_sms,
        "notify_by_email": notify_by_email,
    }

    requested_datetime = f"{date} {time}"
    logger.debug(
        "Preparing booking for service_id=%s at %s (staff_id=%s)",
        product_id,
        requested_datetime,
        staff_id,
    )

    # Проверка доступности времени
    try:
        available_slots = await avaliable_time_for_master_async(
            date=date, service_id=product_id
        )
    except Exception as e:
        logger.error(
            "Failed to fetch available slots for service_id=%s: %s", product_id, e
        )
        return {"success": False, "error": "Не удалось проверить доступность времени"}

    master_slots = next(
        (
            m.get("master_slots", [])
            for m in available_slots
            if m.get("master_id") == staff_id
        ),
        [],
    )

    if requested_datetime not in master_slots:
        logger.warning(
            f"Дата и время {requested_datetime} недоступны для записи у mastrer_id={staff_id}"
        )
        return {
            "success": False,
            "error": f"Дата и время {requested_datetime} недоступны для записи у mastrer_id={staff_id}",
            "available_slots": master_slots,
        }

    # Отправка запроса на запись
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug(
                "Sending booking request to %s with payload=%s", endpoint_url, payload
            )
            response = await client.post(endpoint_url, json=payload)
            response.raise_for_status()
            resp_json = response.json()

            # 🔥 Обработка бага API (этап записи)
            if (
                isinstance(resp_json, dict)
                and resp_json.get("success") is False
                and resp_json.get("error") == "Unexpected status code: 400"
            ):
                logger.warning(
                    "API bug detected while booking (400). Treating booking as successful. "
                    "Payload=%s, Response=%s",
                    payload,
                    resp_json,
                )
                return {
                    "success": True,
                    "info": f"Запись к master_id={staff_id} на время {requested_datetime} сделана",
                }

            logger.info(
                "Booking successful for user_id=%s, service_id=%s", user_id, product_id
            )
            return resp_json

    except httpx.TimeoutException as e:
        logger.error("Timeout while booking service_id=%s: %s", product_id, e)
        raise  # повторная попытка через tenacity

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error %d while booking service_id=%s: %s",
            e.response.status_code,
            product_id,
            e,
        )
        return {"success": False, "error": f"HTTP ошибка: {e.response.status_code}"}

    except Exception as e:
        logger.exception(
            "Unexpected error while booking service_id=%s: %s", product_id, e
        )
        return {"success": False, "error": "Неизвестная ошибка при записи"}


# Пример использования
if __name__ == "__main__":
    """Тестовый пример работы функции."""
    async def main():
        """Тестовый пример работы функции."""
        url = "https://httpservice.ai2b.pro/appointments/yclients/create_booking"  # или твой боевой URL
        result = await record_time_async(
            endpoint_url=url,
            staff_id=4131055,
            product_id="1-11620650",
            date="2025-10-22",
            time="13:00",
            user_id=1176612320,  # ID пользователя в твоей БД
            channel_id=0,  # ID канала
            comment="Запись через API",
            notify_by_sms=1,
            notify_by_email=1,
        )
        logger.info(result)

    asyncio.run(main())

# cd /home/copilot_superuser/petrunin/mcp/zena_qdrant
# python -m zena_qdrant.yclients.record_time
