"""MCP-сервер для переноса урока на другой день.

Action-tool: перенос существующего урока в GO CRM.
Единый контракт ответов: Payload (ok/err).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err

from ..crm.crm_update_client_lesson import go_update_client_lesson  # type: ignore


logger = logging.getLogger(__name__)

tool_update_client_lesson = FastMCP(name="update_client_lesson")


@tool_update_client_lesson.tool(
    name="update_client_lesson",
    description=(
        "Перенос урока на другую дату и время.\n\n"
        "**Назначение:**\n"
        "Используется для переноса урока на другой день и время. "
        "Применяется при онлайн-бронировании.\n\n"
        "**Args:**\n"
        "- phone (`str`, required): Телефон клиента.\n"
        "- channel_id (`str`, required): ID учебной организации.\n"
        "- record_id (`str`, required): ID урока, который нужно перенести.\n"
        "- teacher (`str`, required): Имя преподавателя.\n"
        "- new_date (`str`, required): Новая дата урока (DD.MM.YYYY).\n"
        "- new_time (`str`, required): Новое время урока (HH:MM).\n"
        "- service (`str`, required): Название урока.\n"
        "- reason (`str`, required): Причина переноса урока.\n\n"
        "**Returns:**\n"
        "- Payload[str]\n"
    ),
)
async def update_client_lesson_go(
    phone: str,
    channel_id: str,
    record_id: str,
    teacher: str,
    new_date: str,
    new_time: str,
    service: str,
    reason: str,
) -> Payload[str]:
    """Перенести урок клиента (fail-fast + CRM слой возвращает Payload)."""
    # ------------------------------------------------------------------
    # 1) Fail-fast: обязательные строки
    # ------------------------------------------------------------------
    required_fields: dict[str, str] = {
        "phone": phone,
        "channel_id": channel_id,
        "record_id": record_id,
        "teacher": teacher,
        "new_date": new_date,
        "new_time": new_time,
        "service": service,
        "reason": reason,
    }

    for field, value in required_fields.items():
        if not isinstance(value, str) or not value.strip():
            return err(
                code="validation_error",
                error=f"Поле '{field}' не задано. Запросите у клиента '{field}'.",
            )

    # ------------------------------------------------------------------
    # 2) Fail-fast: формат даты/времени (как ожидает GO слой)
    # ------------------------------------------------------------------
    # new_date: DD.MM.YYYY или YYYY-MM-DD (GO-слой сам нормализует),
    # но здесь проверяем, чтобы LLM не слал мусор.
    date_s = new_date.strip()
    ok_date = False
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            datetime.strptime(date_s, fmt)
            ok_date = True
            break
        except ValueError:
            continue
    if not ok_date:
        return err(
            code="validation_error",
            error="Некорректный формат new_date. Ожидается DD.MM.YYYY (или YYYY-MM-DD).",
        )

    # new_time: HH:MM
    try:
        datetime.strptime(new_time.strip(), "%H:%M")
    except ValueError:
        return err(
            code="validation_error",
            error="Некорректный формат new_time. Ожидается HH:MM.",
        )

    # ------------------------------------------------------------------
    # 3) CRM-вызов: go_update_client_lesson уже возвращает Payload[str]
    # ------------------------------------------------------------------
    try:
        return await go_update_client_lesson(
            phone=phone,
            channel_id=channel_id,
            record_id=record_id,
            instructor_name=teacher,
            new_date=new_date,
            new_time=new_time,
            service=service,
            reason=reason,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # Фолбэк на случай неожиданного исключения в CRM-слое.
        logger.exception("[update_client_lesson] unexpected error: %s", exc)
        return err(
            code="unexpected_error",
            error="Не удалось перенести урок. Попробуйте позже или обратитесь к администратору.",
        )
