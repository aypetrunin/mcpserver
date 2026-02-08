"""MCP-сервер для удаления записей услуг клиента.

Инструмент используется ТОЛЬКО для полного отказа от услуги.
Для переноса даты/времени используется record_reschedule.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err

from ..crm.crm_delete_client_record import delete_client_record  # type: ignore


logger = logging.getLogger(__name__)

tool_record_delete = FastMCP(name="record_delete")


@tool_record_delete.tool(
    name="record_delete",
    description=(
        "Отмена (удаление) записи клиента на услугу в CRM.\n\n"
        "ИСПОЛЬЗУЙ ТОЛЬКО КОГДА:\n"
        "- Клиент хочет полностью ОТКАЗАТЬСЯ от услуги.\n"
        "- Клиент просит отменить, удалить, аннулировать запись.\n"
        "- Клиент говорит, что не придёт и запись больше не нужна.\n\n"
        "НЕ ИСПОЛЬЗУЙ КОГДА:\n"
        "- Клиент хочет изменить дату, время, мастера или филиал.\n"
        "- Клиент говорит «перенести», «поменять время», «перезаписаться».\n"
        "- Клиент хочет записаться на другое время вместо текущего.\n"
        "В этих случаях НУЖНО использовать инструмент `record_reschedule`.\n\n"
        "ВАЖНО:\n"
        "- Если формулировка пользователя двусмысленная "
        "(например: «не получится», «можно изменить?»),\n"
        "  СНАЧАЛА уточни намерение и НЕ вызывай инструмент.\n\n"
        "Args:\n"
        "- user_companychat (str, required): ID пользователя.\n"
        "- office_id (str, required): ID канала / филиала.\n"
        "- record_id (str, required): ID записи в CRM.\n\n"
        "Returns (единый контракт):\n"
        "- ok(data)\n"
        "- err(code, error)\n"
    ),
)
async def delete_records(
    user_companychat: str,
    office_id: str,
    record_id: str,
) -> Payload[Any]:
    """Удалить запись клиента на услугу в CRM."""
    # ------------------------------------------------------------------
    # 1. Валидация аргументов tool-а (пользовательский ввод)
    # ------------------------------------------------------------------
    # Что делаем:
    # - все id приходят строками
    # - приводим к int ОДИН РАЗ
    # - ошибки формата -> validation_error
    try:
        user_id_int = int(user_companychat)
        office_id_int = int(office_id)
        record_id_int = int(record_id)
    except (TypeError, ValueError):
        return err(
            code="validation_error",
            error="Некорректные параметры: user_companychat, office_id и record_id должны быть числами.",
        )

    logger.info(
        "[record_delete] вход | user=%s office_id=%s record_id=%s",
        user_id_int,
        office_id_int,
        record_id_int,
    )

    # ------------------------------------------------------------------
    # 2. Вызов CRM-слоя
    # ------------------------------------------------------------------
    # Что делаем:
    # - бизнес-логика удаления лежит В CRM-функции
    # - она уже обязана возвращать Payload (ok/err)
    try:
        result = await delete_client_record(
            user_companychat=user_id_int,
            office_id=office_id_int,
            record_id=record_id_int,
        )
        return result

    except asyncio.CancelledError:
        # ------------------------------------------------------------------
        # 3. CancelledError НЕ превращаем в err
        # ------------------------------------------------------------------
        # Что делаем:
        # - CancelledError используется supervisor'ом (SIGTERM/SIGINT)
        # - его нельзя "глотать", иначе shutdown сломается
        raise

    except Exception as exc:
        # ------------------------------------------------------------------
        # 4. Защитный fallback (на случай бага в CRM-слое)
        # ------------------------------------------------------------------
        # Что делаем:
        # - сюда не должны попадать штатные ошибки
        # - логируем максимально подробно
        # - наружу отдаём единый err без деталей
        logger.exception(
            "[record_delete] unexpected error | user=%s office_id=%s record_id=%s err=%s",
            user_id_int,
            office_id_int,
            record_id_int,
            exc,
        )
        return err(
            code="internal_error",
            error="Не удалось отменить запись. Попробуйте позже.",
        )
