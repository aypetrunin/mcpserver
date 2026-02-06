"""Поиск свободных слотов по мастерам.

Поддерживает:
- одиночную услугу: result.service.staff[].dates -> master/slots
- комплекс: result.avaliable_sequences -> sequences + short_list

Главная цель:
- не читать settings при импорте модуля;
- не хранить URL из settings как глобальную константу.

Тайм-зоны:
- если слот содержит TZ/offset (ISO8601 "+03:00" или "Z") — парсим как есть;
- если TZ/offset отсутствует ("YYYY-MM-DD HH:MM") — считаем локальным временем агента.
"""

from __future__ import annotations

from datetime import date as date_type, datetime
import logging
from typing import Any

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ..timezone_utils import now_local, parse_slot
from ._crm_http import crm_timeout_s, crm_url


logger = logging.getLogger(__name__.split(".")[-1])

DT_FMT_DATE = "%Y-%m-%d"
DT_FMT_SLOT = "%Y-%m-%d %H:%M"

PRODUCT_PATH = "/appointments/yclients/product"


def _parse_date(value: str) -> date_type | None:
    """Парсит дату в формате YYYY-MM-DD."""
    try:
        return datetime.strptime(value, DT_FMT_DATE).date()
    except ValueError:
        return None


def _error_tuple(message: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Возвращает результат в ожидаемом формате с ошибкой."""
    return ([{"success": False, "error": message}], [])


def filter_sequences_list(name: str, sequences_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Фильтрует список последовательностей по названию услуги."""
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
    """Оставляет только будущие слоты с учётом тайм-зоны агента."""
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
    """Обновляет мастеров в шагах комплекса по service_id."""
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
    """Строит сокращённый список последовательностей комплекса."""
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
    """Выполняет запрос к CRM product и возвращает JSON."""
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
    """Возвращает список слотов по мастерам или список последовательностей комплекса."""
    if not isinstance(service_id, str) or not service_id.strip():
        return _error_tuple("Не задан service_id")

    if not isinstance(server_name, str) or not server_name.strip():
        return _error_tuple("Не задан server_name (нужен для TZ)")

    d = _parse_date(date)
    if d is None:
        return _error_tuple(f"Неверный формат даты: {date}. Ожидается 'YYYY-MM-DD'")

    today = now_local(server_name).date()
    if d < today:
        return _error_tuple(
            f"Нельзя записаться на прошедшее число. Сегодня {today.strftime(DT_FMT_DATE)}"
        )

    payload = {"service_id": service_id, "base_date": date}
    effective_timeout = crm_timeout_s(timeout)

    try:
        resp_json = await _fetch_product(payload=payload, timeout_s=effective_timeout)
    except httpx.HTTPStatusError as e:
        logger.warning(
            "avaliable_time_for_master_list HTTP status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return [], []
    except httpx.RequestError as e:
        logger.warning("avaliable_time_for_master_list request error: %s", e)
        return [], []
    except Exception as e:
        logger.exception(
            "avaliable_time_for_master_list unexpected error payload=%s: %s",
            payload,
            e,
        )
        return [], []

    if resp_json.get("success") is not True:
        return [], []

    result = resp_json.get("result") or {}

    service_obj = result.get("service")
    if isinstance(service_obj, dict):
        staff_list = service_obj.get("staff", [])
        if not isinstance(staff_list, list):
            return [], []

        product_name = service_name.split(",")[0].strip()
        sequences_list: list[dict[str, Any]] = []

        for item in staff_list:
            if not isinstance(item, dict):
                continue

            dates = item.get("dates")
            if not isinstance(dates, list):
                continue

            dates_str = [s for s in dates if isinstance(s, str)]

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

        sequences_list = filter_sequences_list(product_name, sequences_list)
        sequences_list = filter_future_slots(server_name, sequences_list)
        return sequences_list, []

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
