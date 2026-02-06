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

4) Временные слоты CRM приходят уже с учётом тайм-зоны.
   Поэтому:
   - если в строке слота есть TZ/offset (ISO8601 +03:00 / Z) — парсим как есть
   - если TZ/offset отсутствует — считаем, что это локальное время агента (server TZ),
     и "приклеиваем" TZ агента для корректных сравнений.

ВАЖНО:
Тайм-зона выбирается по server_name (MCP_TZ_<SERVER>).

Все филиалы, обслуживаемые данным сервером, считаются находящимися
в одной тайм-зоне. Привязки TZ к office_id не используется.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, date as date_type
from typing import Any, Optional

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ..timezone_utils import now_local, parse_slot  # <-- ВАЖНО: универсальный парсер слота
from ._crm_http import crm_timeout_s, crm_url

logger = logging.getLogger(__name__.split(".")[-1])

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
    - master_slots: список свободных слотов (строки "YYYY-MM-DD HH:MM" или ISO8601)
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


def _filter_future_slots(
    server_name: str,
    slots: list[str],
    now: datetime,
) -> list[str]:
    """
    Оставляем только слоты, которые строго позже текущего времени.

    slots — список строк слотов (могут быть как без TZ, так и с TZ/offset),
    now   — текущее время (timezone-aware) в TZ агента.
    """
    out: list[str] = []
    for s in slots:
        try:
            if parse_slot(server_name, s, fmt_no_tz=DT_FMT_SLOT) > now:
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
    server_name: str,
    count_slots: int = 30,
    timeout: float = 0.0,
) -> list[dict[str, Any]]:
    """
    Основная функция: вернуть свободные слоты по мастерам для одиночной услуги.

    Параметры:
    - date: строка 'YYYY-MM-DD'
    - service_id: id услуги (строка)
    - server_name: логическое имя агента/сервера (например "sofia") для выбора TZ из env MCP_TZ_<SERVER>
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

    # 1.1) Валидация server_name (нужен для TZ)
    if not isinstance(server_name, str) or not server_name.strip():
        logger.warning("Неверный server_name=%r", server_name)
        return []

    # 2) Валидация даты
    d = _parse_date(date)
    if d is None:
        logger.warning("Неверный формат date=%r (ожидается YYYY-MM-DD)", date)
        return [{"success": False, "error": f"Неверный формат даты: {date}. Ожидается 'YYYY-MM-DD'"}]

    # Текущее время считаем в TZ агента
    now = now_local(server_name)
    today = now.date()

    if d < today:
        return [
            {
                "success": False,
                "error": (
                    "Нельзя записаться на прошедшую дату. "
                    f"Сегодня {today.strftime(DT_FMT_DATE)}"
                ),
            }
        ]

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
                # slot может быть с TZ/offset -> parse_slot сохранит tzinfo
                parsed_pairs.append((parse_slot(server_name, s, fmt_no_tz=DT_FMT_SLOT), s))
            except ValueError:
                continue
        parsed_pairs.sort(key=lambda x: x[0])

        dates_sorted = [s for _, s in parsed_pairs]

        # Оставляем будущие и обрезаем до count_slots
        future = _filter_future_slots(server_name, dates_sorted, now)[:count_slots]

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
