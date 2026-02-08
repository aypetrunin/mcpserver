"""MCP-сервер для поиска расписания уроков клиента."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok

from ..crm.crm_get_client_lessons import go_get_client_lessons  # type: ignore


logger = logging.getLogger(__name__)

tool_get_client_lessons = FastMCP(name="get_client_lessons")


@tool_get_client_lessons.tool(
    name="get_client_lessons",
    description=(
        "Получение расписания уроков.\n\n"
        "**Назначение:**\n"
        "Используется для получения расписания уроков клиента с целью "
        "последующего переноса выбранного урока на другой день. "
        "Также применяется при онлайн-бронировании.\n\n"
        "**Примеры запросов:**\n"
        '- "Нужно перенести урок"\n'
        '- "Ребёнок заболел, не сможем прийти"\n'
        '- "Покажи расписание"\n\n'
        "**Args:**\n"
        "- phone (`str`, required): Телефон клиента.\n"
        "- channel_id (`str`, required): ID учебной организации.\n\n"
        "**Returns:**\n"
        "- Payload[dict]\n"
    ),
)
async def get_client_lessons_go(
    phone: str,
    channel_id: str,
) -> Payload[Any]:
    """
    Описание результата.

    Контракт:
    - ok(data)  — CRM ответила корректно (уроки могут отсутствовать)
    - err(...)  — ошибка валидации / сети / CRM
    """
    # --- 1. Валидация ---
    if not phone or not phone.strip():
        return err(
            code="validation_error",
            error="Параметр phone не должен быть пустым.",
        )

    try:
        channel_id_int = int(channel_id)
    except ValueError:
        return err(
            code="validation_error",
            error="Некорректный channel_id: ожидается числовое значение.",
        )

    logger.info(
        "[get_client_lessons] phone=%s channel_id=%s",
        phone,
        channel_id_int,
    )

    # --- 2. Вызов CRM ---
    try:
        response = await go_get_client_lessons(
            phone=phone,
            channel_id=channel_id_int,
        )

    except Exception as exc:
        logger.exception("[get_client_lessons] CRM call failed: %s", exc)
        return err(
            code="crm_error",
            error="Не удалось получить расписание уроков. Попробуйте позже.",
        )

    # --- 3. Нормализация результата ---
    # Здесь мы НЕ требуем success от CRM в payload-е,
    # мы смотрим на факт успешного выполнения запроса.
    return ok(response)
