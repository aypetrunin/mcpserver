"""Модуль поиска свободных слотов по мастерам.

Поиск ведется через API CRM gateway (CRM_BASE_URL).
"""

import asyncio
from datetime import datetime
import logging
from typing import Any, Dict, List

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


# Настройка логгера
logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(CRM_HTTP_RETRIES),
    wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def avaliable_time_for_master_async(
    date: str,
    service_id: str,
    count_slots: int = 30,
    timeout: float = CRM_HTTP_TIMEOUT_S,
) -> List[Dict[str, Any]]:
    """Асинхронный запрос на получение доступных слотов по мастерам для указанной услуги.

    :param date: Дата в формате 'YYYY-MM-DD' (на будущее — может использоваться на бэкенде).
    :param service_id: ID услуги, например "1-20347221".
    :param count_slots: Максимальное количество слотов на мастера.
    :param timeout: Таймаут запроса в секундах.
    :return: Список словарей с информацией о мастерах и их слотах.
    """
    logger.info("===crm.avaliable_time_for_master_async===")

    if not service_id or not isinstance(service_id, str):
        logger.warning("Invalid service_id provided: %s", service_id)
        return []

    url = f"{CRM_BASE_URL}/appointments/yclients/product"  # Убраны пробелы!

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info("Sending request to %s with service_id=%s", url, service_id)
            response = await client.post(
                url=url,
                json={"service_id": service_id, "base_date": date},
            )
            response.raise_for_status()
            resp_json = response.json()

    except httpx.TimeoutException as e:
        logger.error(
            "Timeout while fetching avaliable time for service_id=%s: %s", service_id, e
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
        logger.warning("API вернул success=False для service_id=%s", service_id)
        return []

    result = resp_json.get("result") or {}

    # Проверка на одиночную услугу с "service"
    service_obj = result.get("service")
    if service_obj and isinstance(service_obj, dict):
        staff_list = service_obj.get("staff", [])
        results = [
            {
                "office_id": service_id.split('-')[0],
                "master_name": item["name"],
                "master_id": item["id"],
                "master_slots": sorted( item.get("dates", []), key=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M"))[:count_slots],
            }
            for item in staff_list
            if isinstance(item.get("dates"), list)
        ]
        logger.info(results)
        return results
    return []



# Пример использования
if __name__ == "__main__":
    """Тестовый пример работы функции."""

    async def main()->None:
        """Тестовый пример работы функции."""
        date = "2025-11-29"
        # service_id = "1-19501163"
        service_id = "7-2950601"
        # service_id = "7-2950601, 7-2950603"
        logger.info("Доступные мастера:")
        result = await avaliable_time_for_master_async(date=date, service_id=service_id)
        logger.info(result)

    asyncio.run(main())

# cd /home/copilot_superuser/petrunin/zena
# uv run python -m mcpserver.src.crm.avaliable_time_for_master