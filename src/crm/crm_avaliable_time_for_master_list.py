# src/crm/crm_avaliable_time_for_master_list.py
"""
Поиск свободных слотов по мастерам.

Поддерживает:
- одиночную услугу: result.service.staff[].dates -> master/slots
- комплекс: result.avaliable_sequences -> sequences + short_list

Главная цель этой версии:
- НЕ читать settings при импорте модуля (никаких S = get_settings() сверху)
- НЕ хранить URL, построенный из settings, как глобальную константу
  (URL строим лениво в момент реального запроса)

ВАЖНО ПРО ВРЕМЯ / ТАЙМ-ЗОНЫ
---------------------------
1) Тайм-зона привязана к MCP-серверу (агенту): MCP_TZ_<SERVER>.
   Все филиалы, обслуживаемые данным сервером, находятся в одной тайм-зоне.

2) Слоты, приходящие из CRM, считаются "уже в правильной тайм-зоне".
   На практике это значит:
   - если строка слота содержит TZ/offset (ISO8601 "+03:00" или "Z") — парсим как есть;
   - если TZ/offset отсутствует (например "YYYY-MM-DD HH:MM") — считаем это локальным временем агента
     и "приклеиваем" TZ агента.

Для этого используем timezone_utils.parse_slot(...) и timezone_utils.now_local(...).
"""

from __future__ import annotations

import logging
from datetime import datetime, date as date_type
from typing import Any, Optional

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ..timezone_utils import now_local, parse_slot
from ._crm_http import crm_timeout_s, crm_url

logger = logging.getLogger(__name__.split(".")[-1])

DT_FMT_DATE = "%Y-%m-%d"
DT_FMT_SLOT = "%Y-%m-%d %H:%M"

# Относительный путь к CRM-методу.
# Важно: это безопасная константа, она не зависит от env/settings.
PRODUCT_PATH = "/appointments/yclients/product"


def _parse_date(value: str) -> Optional[date_type]:
    """Парсим дату формата YYYY-MM-DD. Если формат неверный — возвращаем None."""
    try:
        return datetime.strptime(value, DT_FMT_DATE).date()
    except ValueError:
        return None


def _error_tuple(message: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Возвращаем результат в ожидаемом формате функции:
    (sequences_list, short_list), но с ошибкой в sequences_list.
    """
    return ([{"success": False, "error": message}], [])


def filter_sequences_list(name: str, sequences_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Фильтр "по названию услуги" -> ожидаемое имя мастера (как было у вас).

    Если маппинг не найден — возвращаем список как есть.
    """
    map_name = {
        "Прессотерапия": "Прессотерапия",
        "Роликовый массажер": "Ролик",
        "Термотерапия": "Термотерапия",
        "Электролиполиз": "Токовые Процедуры",
        "Электромиостимуляция": "Токовые Процедуры",
    }
    expected = map_name.get(name)
    if not expected:
        return sequences_list
    return [item for item in sequences_list if item.get("master_name") == expected]


def filter_future_slots(server_name: str, masters_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Оставляем только будущие слоты (slot_datetime > now) с учётом TZ агента.

    Вход:
    [
      {"master_name": ..., "master_id": ..., "master_slots": ["YYYY-MM-DD HH:MM" | ISO8601, ...]},
      ...
    ]
    """
    now = now_local(server_name)
    result: list[dict[str, Any]] = []

    for master in masters_data:
        slots = master.get("master_slots") or []
        if not isinstance(slots, list):
            slots = []

        filtered_slots: list[str] = []
        for slot in slots:
            if not isinstance(slot, str):
                continue
            try:
                if parse_slot(server_name, slot, fmt_no_tz=DT_FMT_SLOT) > now:
                    filtered_slots.append(slot)
            except ValueError:
                # Если CRM прислала слот в непредвиденном формате — просто пропускаем
                continue

        result.append(
            {
                "master_name": master.get("master_name"),
                "master_id": master.get("master_id"),
                "master_slots": filtered_slots,
            }
        )

    return result


def update_services_in_sequences(data: dict[str, Any]) -> dict[str, Any]:
    """
    Для "комплекса" вы делали подмену master_id/master_name в шаге на основе service_id.
    Оставляем как есть — это бизнес-правило.
    """
    replacements: dict[str, dict[str, str]] = {
        "2950601": {"master_id": "881127", "master_name": "Термотерапия"},
        "2950597": {"master_id": "864147", "master_name": "Прессотерапия"},
        "2950609": {"master_id": "914499", "master_name": "Ролик"},
        "2950603": {"master_id": "914503", "master_name": "Токовые Процедуры"},
    }

    result = data.get("result")
    if not isinstance(result, dict):
        return data

    seqs = result.get("avaliable_sequences")
    if not isinstance(seqs, list):
        return data

    for seq in seqs:
        if not isinstance(seq, dict):
            continue
        steps = seq.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            rid = step.get("service_id")
            if rid in replacements:
                step["master_id"] = replacements[rid]["master_id"]
                step["master_name"] = replacements[rid]["master_name"]

    return data


def avaliable_sequences_short(avaliable_sequences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Сокращённая форма списка "комплексных" последовательностей.
    """
    result: list[dict[str, Any]] = []
    for seq in avaliable_sequences:
        if not isinstance(seq, dict):
            continue
        steps = seq.get("steps")
        if not isinstance(steps, list):
            continue

        result.append(
            {
                "sequence_id": seq.get("sequence_id"),
                "start_time": seq.get("total_start_time"),
                "services": [
                    {
                        "product_id": "7-" + str(step.get("service_id")),
                        "master_id": step.get("master_id"),
                        "master_name": step.get("master_name"),
                        "date_time": step.get("start_time"),
                    }
                    for step in steps
                    if isinstance(step, dict)
                ],
            }
        )
    return result


@CRM_HTTP_RETRY
async def _fetch_product(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    """
    Низкоуровневый вызов CRM.

    Важно:
    - URL строим ЛЕНИВО: crm_url(PRODUCT_PATH) внутри функции,
      поэтому при импорте модуля settings не читаются.
    - retry делает декоратор @CRM_HTTP_RETRY (429/5xx/network/timeout).
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


async def avaliable_time_for_master_list_async(
    date: str,
    service_id: str,
    service_name: str,
    *,
    server_name: str,
    count_slots: int = 30,
    timeout: float = 0.0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Главная функция: отдаёт либо список мастеров и слотов (одиночная услуга),
    либо список последовательностей (комплекс).

    Возвращает:
    (sequences_list, short_list)

    где:
    - sequences_list:
        для одиночной услуги:
            [{"master_name": ..., "master_id": ..., "master_slots": [...]}, ...]
        для комплекса:
            [{"sequence_id": ..., "start_time": ...}, ...]
    - short_list:
        для комплекса:
            [{sequence_id, start_time, services:[...]}...]
        иначе []
    """

    # 1) Базовая валидация входных параметров
    if not isinstance(service_id, str) or not service_id.strip():
        return _error_tuple("Не задан service_id")

    if not isinstance(server_name, str) or not server_name.strip():
        return _error_tuple("Не задан server_name (нужен для TZ)")

    d = _parse_date(date)
    if d is None:
        return _error_tuple(f"Неверный формат даты: {date}. Ожидается 'YYYY-MM-DD'")

    # Дата/сегодня считаются в TZ агента
    today = now_local(server_name).date()
    if d < today:
        return _error_tuple(f"Нельзя записаться на прошедшее число. Сегодня {today.strftime(DT_FMT_DATE)}")

    # 2) Пейлоад CRM-запроса
    payload = {"service_id": service_id, "base_date": date}

    # 3) Таймаут: если timeout=0/не задан — берём из settings (лениво)
    effective_timeout = crm_timeout_s(timeout)

    # 4) Запрос к CRM
    try:
        resp_json = await _fetch_product(payload=payload, timeout_s=effective_timeout)
    except httpx.HTTPStatusError as e:
        # Сюда попадём только если ретраи исчерпаны или статус неретраибельный (4xx кроме 429)
        logger.warning(
            "avaliable_time_for_master_list HTTP status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return [], []
    except httpx.RequestError as e:
        # Сюда попадём только если ретраи исчерпаны по сетевым ошибкам
        logger.warning("avaliable_time_for_master_list request error: %s", str(e))
        return [], []
    except Exception as e:  # noqa: BLE001
        logger.exception("avaliable_time_for_master_list unexpected error payload=%s: %s", payload, e)
        return [], []

    # 5) Базовая проверка ответа
    if resp_json.get("success") is not True:
        return [], []

    result = resp_json.get("result") or {}

    # -------------------- Одиночная услуга --------------------
    # В этом режиме CRM отдаёт result.service.staff = список мастеров с датами
    service_obj = result.get("service")
    if isinstance(service_obj, dict):
        staff_list = service_obj.get("staff", [])
        if not isinstance(staff_list, list):
            return [], []

        product_name = (service_name.split(",")[0]).strip()
        sequences_list: list[dict[str, Any]] = []

        for item in staff_list:
            if not isinstance(item, dict):
                continue

            dates = item.get("dates")
            if not isinstance(dates, list):
                continue

            # Слоты — строки (могут быть "YYYY-MM-DD HH:MM" или ISO8601 с TZ/offset)
            dates_str = [s for s in dates if isinstance(s, str)]

            # Сортируем по времени (чтобы slots шли по возрастанию), учитывая TZ
            parsed_pairs: list[tuple[datetime, str]] = []
            for s in dates_str:
                try:
                    parsed_pairs.append((parse_slot(server_name, s, fmt_no_tz=DT_FMT_SLOT), s))
                except ValueError:
                    continue
            parsed_pairs.sort(key=lambda x: x[0])

            dates_sorted = [s for _, s in parsed_pairs][:count_slots]

            sequences_list.append(
                {
                    "master_name": item.get("name"),
                    "master_id": item.get("id"),
                    "master_slots": dates_sorted,
                }
            )

        # Ваши бизнес-фильтры
        sequences_list = filter_sequences_list(product_name, sequences_list)
        sequences_list = filter_future_slots(server_name, sequences_list)
        return sequences_list, []

    # -------------------- Комплекс --------------------
    # Тут CRM отдаёт result.avaliable_sequences = список последовательностей услуг
    resp_json = update_services_in_sequences(resp_json)
    avaliable_sequences = (resp_json.get("result") or {}).get("avaliable_sequences")

    if isinstance(avaliable_sequences, list):
        sequences_list = [
            {"sequence_id": seq.get("sequence_id"), "start_time": seq.get("total_start_time")}
            for seq in avaliable_sequences
            if isinstance(seq, dict)
        ]
        short_list = avaliable_sequences_short(avaliable_sequences)
        return sequences_list, short_list

    return [], []


# """Модуль поиска свободных слотов по мастерам.

# Поиск ведется через API CRM gateway (CRM_BASE_URL).
# """

# import asyncio
# import logging
# import httpx

# from datetime import datetime
# from typing import Any


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
# async def avaliable_time_for_master_list_async(
#     date: str,
#     service_id: str,
#     service_name: str,
#     count_slots: int = 30,
#     timeout: float = CRM_HTTP_TIMEOUT_S,
# ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
#     """Асинхронный запрос на получение доступных слотов по мастерам для указанной услуги.

#     :param date: Дата в формате 'YYYY-MM-DD' (на будущее — может использоваться на бэкенде).
#     :param service_id: ID услуги, например "1-20347221".
#     :param count_slots: Максимальное количество слотов на мастера.
#     :param timeout: Таймаут запроса в секундах.
#     :return: Список словарей с информацией о мастерах и их слотах.
#     """
#     logger.info("===crm_avaliable_time_for_master_list===")

#     if not service_id or not isinstance(service_id, str):
#         logger.warning("Не верный service_id: %s", service_id)
#         return [], []

#     try:
#         input_date = datetime.strptime(date, '%Y-%m-%d').date()
#     except ValueError:
#         logger.warning(f"Неверный формат даты: {date}. Ожидается 'YYYY-MM-DD'")
#         return [{"success": False, "error": f"Неверный формат даты: {date}. Ожидается 'YYYY-MM-DD'"}], []

#     today = datetime.now().date()
#     if input_date < today:
#         logger.warning("Ошибка в выборе даты. Нельзя записаться на прошедшее число: %s", date)
#         return [
#             {"success": False,
#              "error": f"Ошибка в выборе даты. Нельзя записаться на прошедшее число. Напомню, сегодня {today.strftime('%Y-%m-%d')}"}
#         ], []

#     url = f"{CRM_BASE_URL}/appointments/yclients/product"

#     try:
#         async with httpx.AsyncClient(timeout=timeout) as client:
#             logger.info("Отправка запроса на API %s c service_id=%s на дату=%s", url, service_id, date)
#             response = await client.post(
#                 url=url,
#                 json={"service_id": service_id, "base_date": date},
#             )
#             response.raise_for_status()
#             resp_json = response.json()

#     except Exception as e:
#         logger.exception("Ошибка API для service_id=%s: %s", service_id, e)
#         return [], []

#     # Обработка успешного ответа
#     if not resp_json.get("success"):
#         logger.warning("API вернуло success=False для service_id=%s", service_id)
#         return [], []

#     # Одиночная услуга
#     service_obj = resp_json.get("result", {}).get("service")
#     if service_obj and isinstance(service_obj, dict):
#         staff_list = service_obj.get("staff", [])
#         product_name = service_name.split(',')[0]
#         sequences_list = [
#             {
#                 "master_name": item["name"],
#                 "master_id": item["id"],
#                 "master_slots": sorted(
#                     item.get("dates", []),
#                     key=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M")
#                     )[:count_slots],
#             }
#             for item in staff_list if isinstance(item.get("dates"), list)
#         ]
#         sequences_list = filter_sequences_list(product_name, sequences_list)
#         sequences_list = filter_future_slots(sequences_list)
#         return sequences_list, []

#     # Комплекс
#     resp_json_modify  = update_services_in_sequences(resp_json)
#     avaliable_sequences = resp_json_modify.get("result", {}).get("avaliable_sequences")
#     if avaliable_sequences and isinstance(avaliable_sequences, list):
#         # Список для выбора времени.
#         sequences_list = [
#             {'sequence_id': seq['sequence_id'], 'start_time': seq['total_start_time']}
#             for seq in avaliable_sequences
#         ]
#         # Список комплекса по которому нужно записать отдельно услуги.
#         avaliable_sequences_short_list = avaliable_sequences_short(avaliable_sequences)
#         return sequences_list, avaliable_sequences_short_list

#     return [], []


# def update_services_in_sequences(data: dict[str, Any]) -> dict[str, Any]:
#     """Функция замены/согласования в словаре услуг названий на используемые в dikidi."""
#     replacements = {
#         '2950601': {'master_id': '881127', 'master_name': 'Термотерапия'},
#         '2950597': {'master_id': '864147', 'master_name': 'Прессотерапия'},
#         '2950609': {'master_id': '914499', 'master_name': 'Ролик'},
#         '2950603': {'master_id': '914503', 'master_name': 'Токовые Процедуры'}
#     }
#     # Оригинальная структура с доступом к avaliable_sequences
#     for seq in data['result']['avaliable_sequences']:
#         for step in seq['steps']:
#             rid = step['service_id']
#             if rid in replacements:
#                 step['master_id'] = replacements[rid]['master_id']
#                 step['master_name'] = replacements[rid]['master_name']
#     return data

# def avaliable_sequences_short(avaliable_sequences: list[dict[str, Any]]) -> list[dict[str, Any]]:
#     """Получение из полного списка данных укороченного списка достаточного для записи на услуги."""
#     result = [
#         {
#             'sequence_id': seq['sequence_id'],
#             'start_time': seq['total_start_time'],
#             'services': [
#                 {
#                     'product_id': '7-' + step['service_id'],
#                     'master_id': step['master_id'],
#                     'master_name': step['master_name'],
#                     'date_time': step['start_time']
#                 }
#                 for step in seq['steps']
#             ]
#         }
#         for seq in avaliable_sequences
#     ]
#     return result

# def filter_sequences_list(
#     name: str,
#     sequences_list: list[dict[str, Any]]
# ) -> list[dict[str, Any]]:
#     """Функция фильтации списка по названию услуги."""
#     map_name = {
#         "Прессотерапия": "Прессотерапия",
#         "Роликовый массажер": "Ролик",
#         "Термотерапия": "Термотерапия",
#         "Электролиполиз": "Токовые Процедуры",
#         "Электромиостимуляция": "Токовые Процедуры",
#     }
#     filter = [item for item in sequences_list if item['master_name']==map_name.get(name)]
#     return filter


# def filter_future_slots(
#     masters_data: list[dict[str, Any]]
# ) -> list[dict[str, Any]]:
#     """Фильтрует слоты мастеров, оставляя только будущие. НЕ изменяет исходные данные."""
#     now = datetime.now()
    
#     result = []
#     for master in masters_data:
#         filtered_slots = [
#             slot for slot in master['master_slots']
#             if datetime.strptime(slot, '%Y-%m-%d %H:%M') > now
#         ]
        
#         # Создаем новую структуру с отфильтрованными слотами
#         result.append({
#             "master_name": master["master_name"],
#             "master_id": master["master_id"],
#             "master_slots": filtered_slots  # Только будущие слоты
#         })

#     return result



# # Пример использования
# if __name__ == "__main__":
#     """Тестовый пример работы функции."""

#     async def main() -> None:
#         """Тестовый пример работы функции."""
#         date = "2025-11-29"
#         # service_id = "1-19501163"
#         service_id = "7-2950601"
#         service_name = "7-2950601"
#         # service_id = "7-2950601, 7-2950603"
#         logger.info("Доступные мастера:")
#         result = await avaliable_time_for_master_list_async(date=date, service_id=service_id, service_name=service_name)
#         logger.info(result)

#     asyncio.run(main())

# # cd /home/copilot_superuser/petrunin/zena
# # uv run python -m mcpserver.src.crm.avaliable_time_for_master