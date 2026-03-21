"""MCP-сервер для фиксации выбранной клиентом услуги.

State-tool: подтверждает выбор одной услуги и (опционально) валидирует его через Postgres.
"""

from __future__ import annotations

import asyncio
import logging

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err, ok

from ..postgres.postgres_util import get_product_name_for_id  # type: ignore


logger = logging.getLogger(__name__)

tool_remember_product_id = FastMCP(name="remember_product_id")


@tool_remember_product_id.tool(
    name="remember_product_id",
    description=(
        "Подтверждение выбора клиентом одной услуги.\n\n"
        "Примеры:\n"
        "- «Выбираю LPG-массаж»\n"
        "- «Запишите на эпиляцию ног»\n"
        "- «Хочу стрижку модельную»\n\n"
        "**Args:**\n"
        "- session_id (`str`, required): ID диалоговой сессии.\n"
        "- product_id (`str`, required): ID выбранной услуги (формат: 2-113323232).\n"
        "- product_name (`str`, required): Название выбранной услуги.\n\n"
        "**Returns:**\n"
        "- Payload[list[dict]]\n"
    ),
)
async def remember_product_id(
    session_id: str,
    product_id: str,
    product_name: str,
) -> Payload[list[dict[str, str]]]:
    """
    Описание результата.

    Контракт:
    - ok([{"product_id": ..., "product_name": ...}]) — выбор подтверждён и зафиксирован
    - err(code,error) — ошибка валидации или инфраструктуры

    Почему list:
    - чтобы быть совместимым с remember_product_id_list (единый формат item_selected)
    """
    # ------------------------------------------------------------
    # 1) Валидация обязательных полей
    # ------------------------------------------------------------
    if not isinstance(session_id, str) or not session_id.strip():
        return err(
            code="validation_error",
            error="Параметр session_id обязателен и не должен быть пустым.",
        )
    if not isinstance(product_id, str) or not product_id.strip():
        return err(
            code="validation_error",
            error="Параметр product_id обязателен и не должен быть пустым.",
        )
    if not isinstance(product_name, str) or not product_name.strip():
        return err(
            code="validation_error",
            error="Параметр product_name обязателен и не должен быть пустым.",
        )

    # ------------------------------------------------------------
    # 2) Валидация соответствия product_id -> product_name через Postgres
    # ------------------------------------------------------------
    # Что делаем:
    # - берём эталонное имя из БД
    # - сравниваем с тем, что пришло от LLM/пользователя
    # - если не совпало — это validation_error (не internal_error)
    try:
        product_name_for_id = await get_product_name_for_id(product_id=product_id)
    except asyncio.CancelledError:
        # cancel всегда пробрасываем (shutdown-safe)
        raise
    except Exception as exc:
        logger.exception(
            "[remember_product_id] postgres lookup failed product_id=%r: %s",
            product_id,
            exc,
        )
        return err(
            code="storage_error",
            error="Не удалось проверить выбранную услугу. Попробуйте позже.",
        )

    if product_name_for_id is None or not str(product_name_for_id).strip():
        return err(
            code="validation_error",
            error="Выбранная услуга не найдена. Покажи, пожалуйста, найденные услуги ещё раз.",
        )

    # нормализация для сравнения
    if str(product_name_for_id).strip().casefold() != product_name.strip().casefold():
        return err(
            code="validation_error",
            error="Название услуги не совпадает с выбранным ID. Покажи, пожалуйста, найденные услуги ещё раз.",
        )

    # ------------------------------------------------------------
    # 3) Фиксация выбора (state)
    # ------------------------------------------------------------
    # Возвращаем эталонное имя из БД (оно “правильнее”, чем присланное).
    return ok([{"product_id": product_id, "product_name": str(product_name_for_id)}])
