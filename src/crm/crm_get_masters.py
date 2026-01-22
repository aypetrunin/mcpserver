# crm_get_masters.py
"""Модуль получения списка мастеров из CRM."""

import logging
from typing import Any, TypedDict, Literal, cast

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

from .crm_result import Payload, ok, err


logger = logging.getLogger(__name__)


# -------------------- Типы ответа CRM --------------------

class Master(TypedDict, total=False):
    id: int
    name: str


class MastersOk(TypedDict):
    success: Literal[True]
    masters: list[Master]


# -------------------- Основная функция --------------------

@retry(
    stop=stop_after_attempt(CRM_HTTP_RETRIES),
    wait=wait_exponential(
        multiplier=1,
        min=CRM_RETRY_MIN_DELAY_S,
        max=CRM_RETRY_MAX_DELAY_S,
    ),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def get_masters(
    channel_id: int,
    timeout: float = CRM_HTTP_TIMEOUT_S,
) -> Payload[list[Master]]:
    """
    Получить список мастеров для канала.

    Возвращает:
    - ok(list[Master]) — при успехе
    - err(...)         — при ошибке
    """
    logger.info("===crm.get_masters===")
    logger.info("Получение списка мастеров channel_id=%s", channel_id)

    url = f"{CRM_BASE_URL}/appointments/yclients/staff/actual"
    payload = {"channel_id": channel_id}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info("POST %s payload=%r", url, payload)
            response = await client.post(url, json=payload)
            response.raise_for_status()

            # Any допустим ТОЛЬКО здесь
            resp_any: Any = response.json()

    except httpx.TimeoutException as e:
        # timeout / connect ошибки → retry через tenacity
        logger.warning("Таймаут при получении мастеров channel_id=%s: %s", channel_id, e)
        raise

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP %s при получении мастеров channel_id=%s",
            e.response.status_code,
            channel_id,
        )
        return err(
            code="http_error",
            error=f"CRM вернул HTTP {e.response.status_code}",
        )

    except Exception as e:  # noqa: BLE001
        logger.exception(
            "Неожиданная ошибка при получении мастеров channel_id=%s", channel_id
        )
        return err(
            code="unexpected_error",
            error="Неизвестная ошибка при получении списка мастеров",
        )

    # -------------------- Валидация ответа CRM --------------------

    if not isinstance(resp_any, dict):
        return err(
            code="crm_bad_response",
            error="CRM вернул некорректный JSON",
        )

    resp = cast(dict[str, Any], resp_any)

    if not resp.get("success", False):
        return err(
            code="crm_error",
            error="CRM вернул ошибку при получении мастеров",
        )

    masters_raw = resp.get("masters")
    if not isinstance(masters_raw, list):
        return err(
            code="crm_bad_response",
            error="CRM вернул некорректный список мастеров",
        )

    masters: list[Master] = []
    for item in masters_raw:
        if isinstance(item, dict):
            masters.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                }
            )

    return ok(masters)


# ---------------------------------------------------------------------------
# ТЕСТОВЫЙ ПРИМЕР
# ---------------------------------------------------------------------------
# Запуск:
#   cd /home/copilot_superuser/petrunin/zena/mcpserver
#   uv run python -m src.crm.crm_get_masters
#
# ВАЖНО:
# Функция get_masters возвращает Payload:
#   - success=True  → data
#   - success=False → code + error
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    from src.runtime import init_runtime
    
    
    
    async def main() -> None:
        
        init_runtime()
        
        result = await get_masters(channel_id=21)

        if result["success"]:
            # УСПЕХ
            masters = result["data"]
            print(f"Получено мастеров: {len(masters)}")
            for m in masters:
                print(f"- {m.get('id')} | {m.get('name')}")

        else:
            # ОШИБКА (единый формат)
            print("Ошибка при получении мастеров")
            print(f"code : {result['code']}")
            print(f"error: {result['error']}")

    asyncio.run(main())





# crm_get_masters.py
# """Модуль записи на услугу на определенную дату и время.

# Поиск ведется через API CRM gateway (CRM_BASE_URL).
# """

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
# async def get_masters(
#     channel_id: int | None = 0,
#     endpoint_url: str = f"{CRM_BASE_URL}/appointments/yclients/staff/actual",
#     timeout: float = CRM_HTTP_TIMEOUT_S,
# ) -> Dict[str, Any]:
#     """Асинхронная запись пользователя на услугу через API с предварительной проверкой слотов.
#     """
#     logger.info("===get_masters===")
#     logger.info("Получение списка мастеров channel_id=%s", channel_id)
    
#     payload = {
#         "channel_id": channel_id,
#     }

#     try:
#         async with httpx.AsyncClient(timeout=timeout) as client:
#             logger.info(
#                 "Отправка запроса на на получение списка мастеров %s with payload=%s", endpoint_url, payload
#             )
#             response = await client.post(endpoint_url, json=payload)
#             response.raise_for_status()
#             resp_json = response.json()
#             return resp_json

#     except httpx.TimeoutException as e:
#         logger.error("Таймаут при бронировании channel_id=%s: %s", channel_id, e)
#         raise  # повторная попытка через tenacity

#     except httpx.HTTPStatusError as e:
#         logger.error(
#             "Ошибка HTTP %d при бронировании channel_id=%s: %s",
#             e.response.status_code,
#             channel_id,
#             e,
#         )
#         return {"success": False, "error": f"HTTP ошибка: {e.response.status_code}"}

#     except Exception as e:
#         logger.exception(
#             "Неожиданная ошибка при бронировании service_id=%s: %s", channel_id, e
#         )
#         return {"success": False, "error": "Неизвестная ошибка при записи"}


# # Пример использования
# if __name__ == "__main__":
#     """Тестовый пример работы функции."""

#     async def main() -> None:
#         """Тестовый пример работы функции."""
#         result = await get_masters(
#             channel_id=21,  # ID канала
#         )
#         print(result)
#         logger.info(result)

#     asyncio.run(main())

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.crm.crm_get_masters
