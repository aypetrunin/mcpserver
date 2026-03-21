"""MCP-сервер для переноса записей услуг клиента.

Action-tool: переносит существующую запись в CRM.
Контракт:
- ok(data) — перенос выполнен (CRM подтвердила успех)
- err(code,error) — ошибка валидации/CRM/сети/прочее
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok

from ..crm.crm_reschedule_client_record import reschedule_client_record  # type: ignore


logger = logging.getLogger(__name__)

tool_record_reschedule = FastMCP(name="record_reschedule")


@tool_record_reschedule.tool(
    name="record_reschedule",
    description=(
        "Перенос (изменение) существующей записи клиента на услугу в CRM.\n\n"
        "ИСПОЛЬЗУЙ ТОЛЬКО КОГДА:\n"
        "- Клиент хочет ПЕРЕНЕСТИ запись.\n"
        "- Клиент хочет изменить дату, время, мастера или филиал.\n"
        "- Клиент говорит «перезаписаться», «поменять время», «сдвинуть запись».\n\n"
        "НЕ ИСПОЛЬЗУЙ КОГДА:\n"
        "- Клиент хочет полностью отменить или удалить запись.\n"
        "- Клиент говорит «отмените», «я не приду», «удалите запись».\n"
        "В этих случаях НУЖНО использовать инструмент `record_delete`.\n\n"
        "ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ:\n"
        "- У клиента ДОЛЖНЫ быть указаны новая дата (date) и время (time).\n"
        "- Если дата или время не указаны, СНАЧАЛА уточни их и НЕ вызывай инструмент.\n\n"
        "ВАЖНО:\n"
        "- office_id — это ID канала / филиала (тот же смысл, что и channel_id в CRM).\n\n"
        "Args:\n"
        "- user_companychat (str, required): ID пользователя.\n"
        "- office_id (str, required): ID канала / филиала.\n"
        "- record_id (str, required): ID записи в CRM.\n"
        "- master_id (str, required): ID мастера.\n"
        "- date (str, required): YYYY-MM-DD (пример: 2025-07-22).\n"
        "- time (str, required): HH:MM (пример: 08:00, 13:00).\n"
        "- comment (str, optional): комментарий к переносу.\n\n"
        "Returns:\n"
        "- Payload[dict]\n"
    ),
)
async def reschedule_record(
    user_companychat: str,
    office_id: str,
    record_id: str,
    date: str,
    time: str,
    master_id: str,
    comment: str | None = None,
) -> Payload[Any]:
    """Перенести существующую запись клиента в CRM."""
    # ------------------------------------------------------------------
    # 1) Валидация (fail-fast)
    # ------------------------------------------------------------------
    try:
        user_companychat_int = int(user_companychat)
        office_id_int = int(office_id)
        record_id_int = int(record_id)
        master_id_int = int(master_id)
    except (TypeError, ValueError):
        return err(
            code="validation_error",
            error="Некорректные параметры: user_companychat, office_id, record_id, master_id должны быть числами.",
        )

    if not isinstance(date, str) or not date.strip():
        return err(
            code="validation_error",
            error="Параметр date обязателен и не должен быть пустым.",
        )
    if not isinstance(time, str) or not time.strip():
        return err(
            code="validation_error",
            error="Параметр time обязателен и не должен быть пустым.",
        )

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return err(
            code="validation_error",
            error="Некорректный формат date. Ожидается YYYY-MM-DD.",
        )

    try:
        datetime.strptime(time, "%H:%M")
    except ValueError:
        return err(
            code="validation_error", error="Некорректный формат time. Ожидается HH:MM."
        )

    comment_final = (comment or "").strip() or "Автоперенос ботом через API"

    logger.info(
        "[record_reschedule] вход | user=%s office_id=%s record_id=%s master_id=%s date=%s time=%s",
        user_companychat_int,
        office_id_int,
        record_id_int,
        master_id_int,
        date,
        time,
    )

    # ------------------------------------------------------------------
    # 2) Вызов CRM (action)
    # ------------------------------------------------------------------
    try:
        crm_resp = await reschedule_client_record(
            user_companychat=user_companychat_int,
            channel_id=office_id_int,
            record_id=record_id_int,
            master_id=master_id_int,
            date=date,
            time=time,
            comment=comment_final,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("[record_reschedule] CRM call failed: %s", exc)
        return err(
            code="crm_error", error="Не удалось перенести запись. Попробуйте позже."
        )

    # ------------------------------------------------------------------
    # 3) Нормализация ответа
    # ------------------------------------------------------------------
    # Если CRM уже возвращает Payload — можно возвращать как есть.
    if (
        isinstance(crm_resp, dict)
        and crm_resp.get("success") is True
        and "data" in crm_resp
    ):
        return ok(crm_resp["data"])

    if isinstance(crm_resp, dict) and crm_resp.get("success") is False:
        # если CRM отдаёт свой error — вытаскиваем в строку
        crm_error = crm_resp.get("error")
        return err(
            code="crm_error",
            error=str(crm_error) if crm_error else "CRM не смогла перенести запись",
        )

    # Иначе: просто завернём как data, чтобы внешний контракт был стабильным
    return ok(crm_resp)
