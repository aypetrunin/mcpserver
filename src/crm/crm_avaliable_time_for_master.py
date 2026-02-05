# src/crm/crm_avaliable_time_for_master.py
"""
Поиск свободных слотов по мастерам (одиночная услуга).

Ожидаемый ответ CRM: result.service.staff[].dates

Что изменено относительно старой версии:
----------------------------------------
1) Убрали S = get_settings() на уровне модуля.
   Это важно, потому что модуль может быть импортирован ДО init_runtime(),
   и тогда get_settings() может прочитать "пустой" env.

2) Убрали URL_PRODUCT, который строился из settings при импорте.
   Теперь URL строится лениво (в момент реального запроса) через crm_url().

3) Таймаут берём единообразно через crm_timeout_s():
   - если timeout > 0 — используем его
   - иначе берём settings.CRM_HTTP_TIMEOUT_S (лениво)
"""

from __future__ import annotations

import logging
import httpx

from typing import Any, Optional
from dataclasses import dataclass
from datetime import datetime, date as date_type

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url

logger = logging.getLogger(__name__.split('.')[-1])

DT_FMT_DATE = "%Y-%m-%d"
DT_FMT_SLOT = "%Y-%m-%d %H:%M"

# Относительный путь к CRM-методу (безопасная константа, не зависит от env)
PRODUCT_PATH = "/appointments/yclients/product"


@dataclass(frozen=True)
class MasterSlots:
    """
    Результат для одного мастера:
    - office_id: id филиала (если есть в service_id)
    - master_name: имя мастера
    - master_id: id мастера
    - master_slots: список свободных слотов (строки "YYYY-MM-DD HH:MM")
    """

    office_id: str
    master_name: str
    master_id: int
    master_slots: list[str]


def _parse_date(value: str) -> Optional[date_type]:
    """Парсим дату формата YYYY-MM-DD. Если формат неверный — возвращаем None."""
    try:
        return datetime.strptime(value, DT_FMT_DATE).date()
    except ValueError:
        return None


def _filter_future_slots(slots: list[str], now: datetime) -> list[str]:
    """
    Оставляем только слоты, которые строго позже текущего времени.

    slots — список строк "YYYY-MM-DD HH:MM"
    now   — текущее время
    """
    out: list[str] = []
    for s in slots:
        try:
            if datetime.strptime(s, DT_FMT_SLOT) > now:
                out.append(s)
        except ValueError:
            # Если слот в неожиданном формате — просто пропускаем
            continue
    return out


@CRM_HTTP_RETRY
async def _fetch_product(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    """
    Низкоуровневый вызов CRM.

    Важно:
    - URL строится лениво: crm_url(PRODUCT_PATH) внутри функции.
      Это гарантирует, что settings не читаются при импорте модуля.
    - retry (429/5xx/network/timeout) обеспечивает @CRM_HTTP_RETRY.
    """
    client = get_http()
    url = crm_url(PRODUCT_PATH)

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


async def avaliable_time_for_master_async(
    date: str,
    service_id: str,
    *,
    count_slots: int = 30,
    timeout: float = 0.0,
) -> list[dict[str, Any]]:
    """
    Основная функция: вернуть свободные слоты по мастерам для одиночной услуги.

    Параметры:
    - date: строка 'YYYY-MM-DD'
    - service_id: id услуги (строка)
    - count_slots: ограничение на число слотов на мастера
    - timeout: если >0 — используем его, иначе берём settings.CRM_HTTP_TIMEOUT_S (лениво)

    Возвращает:
    - список словарей вида:
      [
        {"office_id": "...", "master_name": "...", "master_id": 123, "master_slots": ["...", ...]},
        ...
      ]
    или (в случае ошибок валидации даты) — список с {"success": False, "error": "..."}.
    """

    # 1) Валидация service_id
    if not isinstance(service_id, str) or not service_id.strip():
        logger.warning("Неверный service_id=%r", service_id)
        return []

    # 2) Валидация даты
    d = _parse_date(date)
    if d is None:
        logger.warning("Неверный формат date=%r (ожидается YYYY-MM-DD)", date)
        return [{"success": False, "error": f"Неверный формат даты: {date}. Ожидается 'YYYY-MM-DD'"}]

    today = datetime.now().date()
    if d < today:
        return [{"success": False, "error": f"Нельзя записаться на прошедшую дату. Сегодня {today.strftime(DT_FMT_DATE)}"}]

    # 3) Готовим payload для CRM
    payload = {"service_id": service_id, "base_date": date}

    # 4) Таймаут: либо параметр timeout, либо из settings (лениво)
    effective_timeout = crm_timeout_s(timeout)

    # 5) Делаем запрос
    try:
        resp_json = await _fetch_product(payload=payload, timeout_s=effective_timeout)
    except httpx.HTTPStatusError as e:
        # Сюда попадём, если retry исчерпан или статус неретраибельный (4xx кроме 429)
        logger.warning(
            "avaliable_time_for_master HTTP status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return []
    except httpx.RequestError as e:
        # Сюда попадём, если retry исчерпан по сетевым ошибкам
        logger.warning("avaliable_time_for_master request error: %s", str(e))
        return []
    except Exception as e:  # noqa: BLE001
        logger.exception("avaliable_time_for_master unexpected error payload=%s: %s", payload, e)
        return []

    # 6) Проверяем базовую структуру ответа
    if resp_json.get("success") is not True:
        return []

    result = resp_json.get("result") or {}
    service_obj = result.get("service")
    if not isinstance(service_obj, dict):
        # Этот модуль — только для одиночной услуги
        return []

    staff_list = service_obj.get("staff", [])
    if not isinstance(staff_list, list):
        return []

    # 7) Обработка результата
    now = datetime.now()

    # У вас office_id извлекался из service_id, если там есть "office-service".
    office_id = service_id.split("-", 1)[0] if "-" in service_id else ""

    out: list[MasterSlots] = []
    for item in staff_list:
        if not isinstance(item, dict):
            continue

        dates = item.get("dates")
        if not isinstance(dates, list):
            continue

        dates_str = [s for s in dates if isinstance(s, str)]

        # Сортировка: битые даты отбрасываем
        parsed_pairs: list[tuple[datetime, str]] = []
        for s in dates_str:
            try:
                parsed_pairs.append((datetime.strptime(s, DT_FMT_SLOT), s))
            except ValueError:
                continue
        parsed_pairs.sort(key=lambda x: x[0])

        dates_sorted = [s for _, s in parsed_pairs]

        # Оставляем будущие и обрезаем до count_slots
        future = _filter_future_slots(dates_sorted, now)[:count_slots]

        out.append(
            MasterSlots(
                office_id=office_id,
                master_name=str(item.get("name", "")),
                master_id=int(item.get("id", 0) or 0),
                master_slots=future,
            )
        )

    # dataclass -> dict
    return [m.__dict__ for m in out]


# """Модуль поиска свободных слотов по мастерам.

# Поиск ведется через API CRM gateway (CRM_BASE_URL).
# """

# import asyncio
# from datetime import datetime
# import logging
# from typing import Any, Dict, List

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


# # Настройка логгера
# logger = logging.getLogger(__name__)


# @retry(
#     stop=stop_after_attempt(CRM_HTTP_RETRIES),
#     wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
#     retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
#     reraise=True,
# )
# async def avaliable_time_for_master_async(
#     date: str,
#     service_id: str,
#     count_slots: int = 30,
#     timeout: float = CRM_HTTP_TIMEOUT_S,
# ) -> List[Dict[str, Any]]:
#     """Асинхронный запрос на получение доступных слотов по мастерам для указанной услуги.

#     :param date: Дата в формате 'YYYY-MM-DD' (на будущее — может использоваться на бэкенде).
#     :param service_id: ID услуги, например "1-20347221".
#     :param count_slots: Максимальное количество слотов на мастера.
#     :param timeout: Таймаут запроса в секундах.
#     :return: Список словарей с информацией о мастерах и их слотах.
#     """
#     logger.info("===crm.avaliable_time_for_master_async===")

#     if not service_id or not isinstance(service_id, str):
#         logger.warning("Invalid service_id provided: %s", service_id)
#         return []

#     url = f"{CRM_BASE_URL}/appointments/yclients/product"  # Убраны пробелы!

#     try:
#         async with httpx.AsyncClient(timeout=timeout) as client:
#             logger.info("Sending request to %s with service_id=%s", url, service_id)
#             response = await client.post(
#                 url=url,
#                 json={"service_id": service_id, "base_date": date},
#             )
#             response.raise_for_status()
#             resp_json = response.json()

#     except httpx.TimeoutException as e:
#         logger.error(
#             "Timeout while fetching avaliable time for service_id=%s: %s", service_id, e
#         )
#         raise  # Повторная попытка через tenacity

#     except httpx.HTTPStatusError as e:
#         logger.error(
#             "HTTP error %d for service_id=%s: %s", e.response.status_code, service_id, e
#         )
#         return []

#     except Exception as e:
#         logger.exception("Unexpected error for service_id=%s: %s", service_id, e)
#         return []

#     # Обработка успешного ответа
#     if not resp_json.get("success"):
#         logger.warning("API вернул success=False для service_id=%s", service_id)
#         return []

#     result = resp_json.get("result") or {}

#     # Проверка на одиночную услугу с "service"
#     service_obj = result.get("service")
#     if service_obj and isinstance(service_obj, dict):
#         staff_list = service_obj.get("staff", [])
#         results = [
#             {
#                 "office_id": service_id.split('-')[0],
#                 "master_name": item["name"],
#                 "master_id": item["id"],
#                 "master_slots": sorted( item.get("dates", []), key=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M"))[:count_slots],
#             }
#             for item in staff_list
#             if isinstance(item.get("dates"), list)
#         ]
#         logger.info(results)
#         return results
#     return []



# # Пример использования
# if __name__ == "__main__":
#     """Тестовый пример работы функции."""

#     async def main()->None:
#         """Тестовый пример работы функции."""
#         date = "2025-11-29"
#         # service_id = "1-19501163"
#         service_id = "7-2950601"
#         # service_id = "7-2950601, 7-2950603"
#         logger.info("Доступные мастера:")
#         result = await avaliable_time_for_master_async(date=date, service_id=service_id)
#         logger.info(result)

#     asyncio.run(main())

# # cd /home/copilot_superuser/petrunin/zena
# # uv run python -m mcpserver.src.crm.avaliable_time_for_master