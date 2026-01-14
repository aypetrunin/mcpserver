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

from .crm_avaliable_time_for_master import avaliable_time_for_master_async

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
async def get_masters(
    channel_id: int | None = 0,
    endpoint_url: str = f"{BASE_URL}/appointments/yclients/staff/actual",
    timeout: float = TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Асинхронная запись пользователя на услугу через API с предварительной проверкой слотов.
    """
    logger.info("===get_masters===")
    print("===get_masters===")
    payload = {
        "channel_id": channel_id,
    }
    logger.info("===get_masters===")
    logger.info(
        "Получение списка мастеров channel_id=%s",
        channel_id,
    )
    # Отправка запроса на запись
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(
                "Отправка запроса на на получение списка мастеров %s with payload=%s", endpoint_url, payload
            )
            response = await client.post(endpoint_url, json=payload)
            response.raise_for_status()
            resp_json = response.json()


            # # 🔥 Обработка бага API (этап записи)
            # if (
            #     isinstance(resp_json, dict)
            #     and resp_json.get("success") is False
            #     and resp_json.get("error") == "Неожиданный код статуса: 400"
            # ):
            #     logger.info(
            #         "Обнаружена ошибка API при бронировании (400). Бронирование считается успешным. "
            #         "Payload=%s, Response=%s",
            #         payload,
            #         resp_json,
            #     )
            #     return {
            #         "success": True,
            #         "info": f"Запись к master_id={staff_id} на время {requested_datetime} сделана",
            #     }

            # logger.info(
            #     "Бронирование успешно выполнено для user_id=%s, service_id=%s", user_id, product_id
            # )
            return resp_json

    except httpx.TimeoutException as e:
        logger.error("Таймаут при бронировании channel_id=%s: %s", channel_id, e)
        raise  # повторная попытка через tenacity

    except httpx.HTTPStatusError as e:
        logger.error(
            "Ошибка HTTP %d при бронировании channel_id=%s: %s",
            e.response.status_code,
            channel_id,
            e,
        )
        return {"success": False, "error": f"HTTP ошибка: {e.response.status_code}"}

    except Exception as e:
        logger.exception(
            "Неожиданная ошибка при бронировании service_id=%s: %s", channel_id, e
        )
        return {"success": False, "error": "Неизвестная ошибка при записи"}


# Пример использования
if __name__ == "__main__":
    """Тестовый пример работы функции."""

    async def main() -> None:
        """Тестовый пример работы функции."""
        result = await get_masters(
            channel_id=21,  # ID канала
        )
        print(result)
        logger.info(result)

    asyncio.run(main())

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.crm.crm_get_masters
