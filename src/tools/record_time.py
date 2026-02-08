"""MCP-сервер записи клиента на выбранную услугу на дату и время.

Action-tool: выполняет запись в CRM.
Контракт:
- ok(data) — запись выполнена (CRM подтвердила успех)
- err(code,error) — ошибка валидации/инфраструктуры/CRM
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok

from ..crm.crm_record_time import record_time_async  # type: ignore
from ..postgres.postgres_util import read_secondary_article_by_primary  # type: ignore


logger = logging.getLogger(__name__)

tool_record_time = FastMCP(name="record_time")


@tool_record_time.tool(
    name="record_time",
    description=(
        "Запись клиента на медицинскую услугу в выбранную дату и время.\n\n"
        "**Назначение:**\n"
        "Используется, когда клиент подтвердил желание записаться на конкретную услугу "
        "в указанное время. Фиксирует запись для последующего подтверждения или обработки.\n\n"
        "**Args:**\n"
        "- session_id (`str`, required): ID dialog session.\n"
        "- office_id (`str`, required): ID филиала.\n"
        "- date (`str`, required): Дата записи в формате YYYY-MM-DD (пример: 2025-07-22).\n"
        "- time (`str`, required): Время записи в формате HH:MM (пример: 08:00, 13:00).\n"
        "- product_id (`str`, required): Идентификатор услуги (формат: 1-232324).\n"
        "- client_id (`int`, required): ID клиента.\n"
        "- master_id (`int`, optional): ID мастера.\n\n"
        "**Returns:**\n"
        "- Payload[dict]\n"
    ),
)
async def record_time(
    session_id: str,
    office_id: str,
    date: str,
    time: str,
    product_id: str,
    client_id: int,
    master_id: int = 0,
) -> Payload[Any]:
    """Записать клиента на услугу на указанную дату и время."""
    _ = session_id  # сейчас не используется

    # ------------------------------------------------------------------
    # 1) Валидация входных параметров (fail-fast)
    # ------------------------------------------------------------------
    if not isinstance(product_id, str) or not product_id.strip():
        return err(
            code="validation_error",
            error="Параметр product_id обязателен и не должен быть пустым.",
        )

    try:
        office_id_int = int(office_id)
    except (TypeError, ValueError):
        return err(
            code="validation_error",
            error="Некорректный office_id: ожидается числовое значение.",
        )

    # product_id должен быть вида "число-число"
    parts = product_id.split("-", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return err(
            code="validation_error",
            error="Некорректный product_id: ожидается формат 'число-число', например '1-232324'.",
        )

    try:
        primary_channel_int = int(parts[0])
    except ValueError:
        return err(
            code="validation_error",
            error="Некорректный product_id: первая часть должна быть числом (канал), например '1-232324'.",
        )

    # date/time формат
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

    if not isinstance(client_id, int) or client_id <= 0:
        return err(
            code="validation_error",
            error="Некорректный client_id: ожидается положительное число.",
        )

    if not isinstance(master_id, int) or master_id < 0:
        return err(
            code="validation_error",
            error="Некорректный master_id: ожидается число >= 0.",
        )

    logger.info(
        "[record_time] вход | office_id=%s date=%s time=%s product_id=%s client_id=%s master_id=%s",
        office_id_int,
        date,
        time,
        product_id,
        client_id,
        master_id,
    )

    # ------------------------------------------------------------------
    # 2) Маппинг primary -> secondary product_id (если записываем в другой филиал)
    # ------------------------------------------------------------------
    try:
        if office_id_int != primary_channel_int:
            secondary_product_id = await read_secondary_article_by_primary(
                primary_article=product_id,
                primary_channel=primary_channel_int,
                secondary_channel=office_id_int,
            )
            if not secondary_product_id:
                return err(
                    code="mapping_not_found",
                    error="Не удалось подобрать услугу для выбранного филиала. Покажите список услуг заново.",
                )
            product_id = secondary_product_id

    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception(
            "[record_time] secondary mapping failed | product_id=%s primary_channel=%s office_id=%s err=%s",
            product_id,
            primary_channel_int,
            office_id_int,
            exc,
        )
        return err(
            code="storage_error",
            error="Не удалось подготовить запись. Попробуйте позже.",
        )

    # ------------------------------------------------------------------
    # 3) Вызов CRM (action)
    # ------------------------------------------------------------------
    try:
        crm_resp = await record_time_async(
            date=date,
            time=time,
            product_id=product_id,
            user_id=client_id,
            staff_id=master_id,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("[record_time] CRM call failed: %s", exc)
        return err(
            code="crm_error", error="Не удалось записать на услугу. Попробуйте позже."
        )

    # ------------------------------------------------------------------
    # 4) Нормализация: CRM могла вернуть свой формат
    # ------------------------------------------------------------------
    # Если crm_resp уже Payload — возвращаем как есть.
    if (
        isinstance(crm_resp, dict)
        and crm_resp.get("success") in (True, False)
        and ("data" in crm_resp or "error" in crm_resp)
    ):
        # это уже близко к Payload; но мы не можем гарантировать структуру CRM.
        # Если success=True — оборачиваем в ok(crm_resp), чтобы внешне контракт был стабильным.
        if crm_resp.get("success") is True:
            return ok(crm_resp)
        # если CRM уже отдаёт нормальный code/error — можно прокинуть,
        # но чаще это не так, поэтому нормализуем.
        crm_error = crm_resp.get("error")
        return err(
            code="crm_error",
            error=str(crm_error) if crm_error else "CRM не смогла выполнить запись",
        )

    # иначе просто возвращаем как data
    return ok(crm_resp)
