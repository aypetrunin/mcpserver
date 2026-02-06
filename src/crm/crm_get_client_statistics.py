"""Получает статистику посещений клиента в GO CRM и рассчитывает абонемент."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import re
from typing import Any, Literal, TypedDict

from dateutil.relativedelta import relativedelta
import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url


logger = logging.getLogger(__name__.split(".")[-1])

CLIENT_INFO_PATH = "/appointments/go_crm/client_info"


class ErrorResponse(TypedDict):
    """Описывает ответ с ошибкой."""

    success: Literal[False]
    error: str


class SuccessResponse(TypedDict):
    """Описывает успешный ответ."""

    success: Literal[True]
    message: dict[str, Any]


ResponsePayload = ErrorResponse | SuccessResponse


@CRM_HTTP_RETRY
async def _fetch_client_info(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    """Выполняет запрос к GO CRM и возвращает JSON."""
    client = get_http()
    url = crm_url(CLIENT_INFO_PATH)

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


async def go_get_client_statisics(
    phone: str,
    channel_id: str = "20",
    timeout: float = 0.0,
) -> ResponsePayload:
    """Возвращает статистику посещений и параметры абонемента."""
    if not isinstance(phone, str) or not phone.strip():
        return {"success": False, "error": "Не указан телефон клиента (phone)"}

    if not isinstance(channel_id, str) or not channel_id.strip():
        return {"success": False, "error": "Не указан channel_id"}

    payload = {"channel_id": channel_id, "phone": phone}
    effective_timeout = crm_timeout_s(timeout)

    fallback_err = "Сервис GO CRM временно недоступен. Обратитесь к администратору."

    try:
        resp_json = await _fetch_client_info(payload=payload, timeout_s=effective_timeout)

    except httpx.HTTPStatusError as e:
        logger.warning(
            "http error status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return {"success": False, "error": fallback_err}

    except httpx.RequestError as e:
        logger.warning("request error payload=%s: %s", payload, e)
        return {"success": False, "error": fallback_err}

    except ValueError:
        logger.exception("invalid json payload=%s", payload)
        return {"success": False, "error": fallback_err}

    except Exception as e:
        logger.exception("unexpected error payload=%s: %s", payload, e)
        return {"success": False, "error": fallback_err}

    if resp_json.get("success") is not True:
        logger.warning(
            "no data for channel_id=%s phone=%s",
            channel_id,
            phone,
        )
        return {"success": False, "error": fallback_err}

    visits = resp_json.get("visits", [])
    abonements = resp_json.get("abonements", [])

    if visits == [] and abonements == []:
        return {
            "success": True,
            "message": {
                "message": (
                    "У Вас еще нет посещений, абонемент начнет действовать с даты первого посещения "
                    "в течении 30 дней."
                )
            },
        }

    calc = AbonementCalculator(visits if isinstance(visits, list) else [])
    msg = calc.calculate()

    return {"success": True, "message": msg}


class AbonementCalculator:
    """Рассчитывает параметры абонемента по списку посещений."""

    DATE_FMT = "%d.%m.%Y"
    RE_ABONEMENT = re.compile(r"х(\d+)\s*№(\d+)")

    def __init__(self, records: list[dict[str, Any]]):
        """Создаёт калькулятор абонемента."""
        self.records = records

    def _parse_date(self, s: str) -> datetime | None:
        """Парсит дату DD.MM.YYYY."""
        return datetime.strptime(s, self.DATE_FMT) if s else None

    def _format_date(self, dt: datetime | None) -> str | None:
        """Форматирует дату в DD.MM.YYYY."""
        return dt.strftime(self.DATE_FMT) if dt else None

    def _find_start_record(self) -> dict[str, Any] | None:
        """Находит стартовую запись абонемента."""
        return next(
            (r for r in self.records if r.get("is_start") or r.get("comment") == "СТАРТ"),
            None,
        )

    def _parse_abonement_text(self, text: str) -> tuple[int | None, str | None]:
        """Извлекает количество занятий и номер абонемента из текста."""
        m = self.RE_ABONEMENT.search(text or "")
        if not m:
            return None, None
        return int(m.group(1)), m.group(2)

    def calculate(self) -> dict[str, Any]:
        """Рассчитывает параметры абонемента."""
        start_record = self._find_start_record()

        summary: dict[str, Any] = {
            "abonement_number": None,
            "lessons_total": None,
            "start_date": None,
            "end_date": None,
            "used_lessons": 0,
            "remaining_lessons": None,
            "makeup_lessons": 0,
            "transfers_used": 0,
            "transfers_left": None,
            "next_transfer_after": None,
        }

        if not start_record:
            return summary

        lessons_total, abonement_number = self._parse_abonement_text(start_record.get("abonement", ""))
        summary["lessons_total"] = lessons_total
        summary["abonement_number"] = abonement_number

        start_dt = self._parse_date(start_record.get("date"))
        summary["start_date"] = self._format_date(start_dt)

        end_dt = start_dt + timedelta(days=30) if start_dt else None
        summary["end_date"] = self._format_date(end_dt)

        if not end_dt:
            return summary

        used = 0
        makeup = 0
        transfer_dates: list[datetime] = []

        for r in self.records:
            dt = self._parse_date(r.get("date"))

            if r.get("is_makeup"):
                makeup += 1
                continue

            if r.get("is_start") or r.get("is_finish"):
                continue

            used += 1

            if dt and dt > end_dt:
                transfer_dates.append(dt)

        transfer_dates.sort()

        summary["used_lessons"] = used
        summary["makeup_lessons"] = makeup
        summary["transfers_used"] = len(transfer_dates)

        if lessons_total is not None:
            summary["remaining_lessons"] = max(lessons_total - used, 0)
            summary["transfers_left"] = max(summary["remaining_lessons"] - summary["transfers_used"], 0)

        transfers_used = summary["transfers_used"]
        if transfers_used == 0:
            next_after = end_dt
        elif transfers_used == 1:
            next_after = transfer_dates[-1]
        else:
            next_after = end_dt + relativedelta(months=1)

        summary["next_transfer_after"] = self._format_date(next_after)

        return summary
