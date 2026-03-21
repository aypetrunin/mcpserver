"""MCP-сервер для поиска статистики посещений занятий клиента."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok

from ..crm.crm_get_client_statistics import go_get_client_statisics  # type: ignore


logger = logging.getLogger(__name__)

tool_get_client_statistics = FastMCP(name="get_client_statistics")


@tool_get_client_statistics.tool(
    name="get_client_statistics",
    description=(
        "Получение статистики посещений занятий клиентом.\n\n"
        "**Назначение:**\n"
        "Используется для получения информации о балансе и статистике посещений "
        "занятий клиентом. Может применяться при онлайн-бронировании.\n\n"
        "**Примеры запросов:**\n"
        '- "Какой у меня баланс?"\n'
        '- "Сколько занятий у меня осталось?"\n'
        '- "Покажи статистику."\n'
        '- "Покажи баланс."\n\n'
        "**Args:**\n"
        "- phone (`str`, required): Телефон клиента.\n"
        "- channel_id (`str`, required): ID учебной организации.\n\n"
        "**Returns:**\n"
        "- Payload[dict]\n"
    ),
)
async def get_client_statistics(
    phone: str,
    channel_id: str,
) -> Payload[Any]:
    """
    Описание результата.

    Контракт:
    - ok(data)  — CRM ответила корректно (баланс/статистика могут быть пустыми)
    - err(...)  — ошибка валидации / сети / CRM
    """
    # ------------------------------------------------------------------
    # 1. Валидация входных параметров
    # ------------------------------------------------------------------
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
        "[get_client_statistics] phone=%s channel_id=%s",
        phone,
        channel_id_int,
    )

    # ------------------------------------------------------------------
    # 2. Вызов CRM
    # ------------------------------------------------------------------
    try:
        response = await go_get_client_statisics(
            phone=phone,
            channel_id=channel_id_int,
        )

    except Exception as exc:
        logger.exception("[get_client_statistics] CRM call failed: %s", exc)
        return err(
            code="crm_error",
            error="Не удалось получить статистику посещений. Попробуйте позже.",
        )

    # ------------------------------------------------------------------
    # 3. Нормальный исход
    # ------------------------------------------------------------------
    return ok(response)
