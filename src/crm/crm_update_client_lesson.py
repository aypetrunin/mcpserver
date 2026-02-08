"""Переносит урок клиента в GO CRM на другую дату и время.

Единый контракт ответов:
- ok(data)  -> {"success": True, "data": ...}
- err(...)  -> {"success": False, "code": "...", "error": "..."}
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url
from ._crm_result import Payload, err, ok
from .crm_get_client_statistics import go_get_client_statisics


logger = logging.getLogger(__name__.split(".")[-1])

RESCHEDULE_PATH = "/appointments/go_crm/reschedule_record"


def _validate_nonempty_str(value: Any) -> bool:
    """Вернуть True, если value — непустая строка."""
    return isinstance(value, str) and bool(value.strip())


def _input_error(param_name: str, value: Any) -> Payload[Any]:
    """Fail-fast ошибка валидации входных данных."""
    logger.warning("go_update_client_lesson invalid param '%s': %r", param_name, value)
    return err(
        code="validation_error",
        error=f"Поле '{param_name}' не задано или имеет неверный формат.",
    )


def normalize_date(value: str | None) -> str | None:
    """Нормализует дату в формат DD.MM.YYYY."""
    if not value:
        return None

    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {value}")


@CRM_HTTP_RETRY
async def _reschedule_record_payload(
    payload: dict[str, Any], timeout_s: float
) -> dict[str, Any]:
    """Выполняет запрос переноса урока и возвращает JSON (dict)."""
    client = get_http()
    url = crm_url(RESCHEDULE_PATH)

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


async def go_update_client_lesson(
    phone: str,
    channel_id: str,
    record_id: str,
    instructor_name: str,
    new_date: str,
    new_time: str,
    service: str,
    reason: str,
    timeout: float = 0.0,
) -> Payload[str]:
    """Переносит урок клиента в GO CRM."""
    # ------------------------------------------------------------------
    # 1) Fail-fast валидация входа
    # ------------------------------------------------------------------
    for name, value in (
        ("phone", phone),
        ("channel_id", channel_id),
        ("record_id", record_id),
        ("instructor_name", instructor_name),
        ("new_date", new_date),
        ("new_time", new_time),
        ("service", service),
        ("reason", reason),
    ):
        if not _validate_nonempty_str(value):
            return _input_error(name, value)

    # дата должна быть приводима к DD.MM.YYYY
    try:
        normalized_new_date = normalize_date(new_date) or new_date
    except ValueError:
        return err(
            code="validation_error",
            error=f"Неверный формат даты: {new_date}. Ожидается DD.MM.YYYY.",
        )

    # transfer_date — для проверки лимитов переносов
    try:
        transfer_date = datetime.strptime(normalized_new_date, "%d.%m.%Y")
    except ValueError:
        return err(
            code="validation_error",
            error=f"Неверный формат даты: {new_date}. Ожидается DD.MM.YYYY.",
        )

    # ------------------------------------------------------------------
    # 2) Получаем статистику (лимиты переносов)
    # ------------------------------------------------------------------
    abonent_end_date: Any = None
    next_transfer_after: Any = None

    try:
        statistic = await go_get_client_statisics(phone=phone, channel_id=channel_id)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # это НЕ критично для переноса, но лимит проверить не смогли
        logger.exception("go_update_client_lesson statistics fetch failed: %s", exc)
        statistic = {}

    if isinstance(statistic, dict) and statistic.get("success") is True:
        msg = statistic.get("message") or {}
        if isinstance(msg, dict):
            abonent_end_date = msg.get("end_date")
            next_transfer_after = msg.get("next_transfer_after")

    abonent_end_dt: datetime | None = None
    next_transfer_dt: datetime | None = None

    try:
        if abonent_end_date:
            abonent_end_dt = datetime.strptime(str(abonent_end_date), "%d.%m.%Y")
        if next_transfer_after:
            next_transfer_dt = datetime.strptime(str(next_transfer_after), "%d.%m.%Y")
    except ValueError:
        logger.warning(
            "Некорректные даты из статистики: end_date=%r next_transfer_after=%r",
            abonent_end_date,
            next_transfer_after,
        )

    # Ваша бизнес-логика сохранена:
    # "в этом месяце после окончания абонемента уже было 2 переноса"
    if abonent_end_dt and next_transfer_dt:
        # было: if not (transfer_date <= abonent_end_dt or transfer_date >= next_transfer_dt)
        # читается как "дата попала в запрещённый интервал (abonent_end_dt, next_transfer_dt)"
        if not (transfer_date <= abonent_end_dt or transfer_date >= next_transfer_dt):
            msg = (
                "В этом месяце после окончания абонемента у Вас уже было 2 переноса. "
                f"Вы можете перенести занятие после {next_transfer_dt.strftime('%d.%m.%Y')}."
            )
            logger.warning("%s", msg)
            return err(code="transfer_limit", error=msg)

    # ------------------------------------------------------------------
    # 3) Формируем payload и вызываем GO CRM
    # ------------------------------------------------------------------
    payload: dict[str, str] = {
        "channel_id": channel_id.strip(),
        "phone": phone.strip(),
        "record_id": record_id.strip(),
        "instructor_name": instructor_name.strip(),
        "new_date": normalized_new_date.strip(),
        "new_time": new_time.strip(),
        "service": service.strip(),
        "reason": reason.strip(),
    }

    effective_timeout = crm_timeout_s(timeout)

    try:
        resp_json = await _reschedule_record_payload(
            payload=payload, timeout_s=effective_timeout
        )

    except asyncio.CancelledError:
        raise

    except httpx.HTTPStatusError as e:
        logger.warning(
            "go_update_client_lesson http error status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return err(
            code="crm_http_error",
            error="GO CRM временно недоступен. Обратитесь к администратору.",
        )

    except httpx.RequestError as e:
        logger.warning(
            "go_update_client_lesson request error payload=%s: %s", payload, e
        )
        return err(
            code="crm_network_error",
            error="Сетевая ошибка при обращении к GO CRM. Обратитесь к администратору.",
        )

    except ValueError:
        logger.exception("go_update_client_lesson invalid json payload=%s", payload)
        return err(
            code="invalid_response",
            error="GO CRM вернул некорректный ответ. Обратитесь к администратору.",
        )

    except Exception as e:
        logger.exception(
            "go_update_client_lesson unexpected error payload=%s: %s", payload, e
        )
        return err(
            code="unexpected_error",
            error="Неизвестная ошибка при обращении к GO CRM. Обратитесь к администратору.",
        )

    # ------------------------------------------------------------------
    # 4) Нормализация бизнес-результата GO CRM
    # ------------------------------------------------------------------
    if resp_json.get("success") is not True:
        return err(
            code="crm_rejected",
            error="Ошибка переноса урока. Обратитесь к администратору.",
        )

    api_new_date = str(resp_json.get("new_date", normalized_new_date))
    api_new_time = str(resp_json.get("new_time", new_time))

    return ok(f"Перенос урока выполнен успешно на {api_new_date} {api_new_time}!")
