"""Модуль поиска свободных слотов по мастерам.

Поиск ведется через API https://httpservice.ai2b.pro.
"""

import asyncio
import logging
from typing import Any, Dict, List

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Настройка логгера
logger = logging.getLogger(__name__)

# Константы (лучше вынести в .env или config)
BASE_URL = "https://httpservice.ai2b.pro"
TIMEOUT_SECONDS = 180.0
MAX_RETRIES = 3


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def avaliable_time_for_master_async(
    date: str,
    service_id: str,
    count_slots: int = 30,
    timeout: float = TIMEOUT_SECONDS,
) -> List[Dict[str, Any]]:
    """Асинхронный запрос на получение доступных слотов по мастерам для указанной услуги.

    :param date: Дата в формате 'YYYY-MM-DD' (на будущее — может использоваться на бэкенде).
    :param service_id: ID услуги, например "1-20347221".
    :param count_slots: Максимальное количество слотов на мастера.
    :param timeout: Таймаут запроса в секундах.
    :return: Список словарей с информацией о мастерах и их слотах.
    """
    if not service_id or not isinstance(service_id, str):
        logger.warning("Invalid service_id provided: %s", service_id)
        return []

    url = f"{BASE_URL}/appointments/yclients/product"  # Убраны пробелы!

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug("Sending request to %s with service_id=%s", url, service_id)
            response = await client.post(
                url=url,
                json={"service_id": service_id, "base_date": date},
            )
            response.raise_for_status()
            resp_json = response.json()

    except httpx.TimeoutException as e:
        logger.error(
            "Timeout while fetching available time for service_id=%s: %s", service_id, e
        )
        raise  # Повторная попытка через tenacity

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error %d for service_id=%s: %s", e.response.status_code, service_id, e
        )
        return []

    except Exception as e:
        logger.exception("Unexpected error for service_id=%s: %s", service_id, e)
        return []

    # Обработка успешного ответа
    if not resp_json.get("success"):
        logger.warning("API returned success=False for service_id=%s", service_id)
        return []

    try:
        staff_list = resp_json["result"]["service"]["staff"]
    except KeyError:
        logger.error("Unexpected response structure: %s", resp_json)
        return []

    if staff_list is None:
        return []

    results = [
        {
            "master_name": item["name"],
            "master_id": item["id"],
            "master_slots": item["dates"][:count_slots],
        }
        for item in staff_list
        if "dates" in item and isinstance(item["dates"], list)
    ]

    logger.debug("Found %d masters for service_id=%s", len(results), service_id)
    return results


# Пример использования
if __name__ == "__main__":
    """Тестовый пример работы функции."""

    async def main():
        """Тестовый пример работы функции."""
        date = "2025-10-20"
        service_id = "1-20539533"
        logger.info("Доступные мастера:")
        result = await avaliable_time_for_master_async(date=date, service_id=service_id)
        logger.info(result)

    asyncio.run(main())
