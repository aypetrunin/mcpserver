"""MCP-сервер для записи и обновления анкетных данных клиента.

Action-tool: сохраняет/обновляет анкету в GO CRM.
Единый контракт ответов: Payload (ok/err).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err

from ..crm.crm_update_client_info import go_update_client_info  # type: ignore


logger = logging.getLogger(__name__)

tool_update_client_info = FastMCP(name="update_client_info")


@tool_update_client_info.tool(
    name="update_client_info",
    description=(
        "Сохранение и обновление анкетных данных клиента.\n\n"
        "**Назначение:**\n"
        "Используется для сохранения анкетных данных клиента при первом обращении "
        "или их обновлении в процессе онлайн-бронирования.\n\n"
        "**Args:**\n"
        "- user_id (`str`, required): ID клиента.\n"
        "- channel_id (`str`, required): ID канала.\n"
        "- parent_name (`str`, required): Имя родителя ребёнка.\n"
        "- phone (`str`, required): Телефон клиента.\n"
        "- email (`str`, required): Электронная почта клиента.\n"
        "- child_name (`str`, required): Имя ребёнка.\n"
        "- child_date_of_birth (`str`, required): Дата рождения ребёнка (DD.MM.YYYY).\n"
        "- contact_reason (`str`, required): Причина обращения.\n\n"
        "**Returns:**\n"
        "- Payload[str]\n"
    ),
)
async def update_client_info_go(
    user_id: str,
    channel_id: str,
    parent_name: str,
    phone: str,
    email: str,
    child_name: str,
    child_date_of_birth: str,
    contact_reason: str,
) -> Payload[str]:
    """Сохранить анкетные данные клиента (fail-fast валидируем, дальше прокидываем в CRM-слой)."""
    # ------------------------------------------------------------------
    # 1) Fail-fast валидация обязательных полей (чтобы не дёргать CRM зря)
    # ------------------------------------------------------------------
    required_fields: dict[str, str] = {
        "user_id": user_id,
        "channel_id": channel_id,
        "parent_name": parent_name,
        "phone": phone,
        "email": email,
        "child_name": child_name,
        "child_date_of_birth": child_date_of_birth,
        "contact_reason": contact_reason,
    }

    for field, value in required_fields.items():
        if not isinstance(value, str) or not value.strip():
            return err(
                code="validation_error",
                error=f"Поле '{field}' не задано. Запросите у клиента '{field}'.",
            )

    # Формат даты DD.MM.YYYY (как в проекте)
    try:
        datetime.strptime(child_date_of_birth.strip(), "%d.%m.%Y")
    except ValueError:
        return err(
            code="validation_error",
            error="Некорректный формат child_date_of_birth. Ожидается DD.MM.YYYY.",
        )

    # Лёгкая sanity-check email (без жёстких регэкспов)
    email_s = email.strip()
    if "@" not in email_s or "." not in email_s:
        return err(
            code="validation_error",
            error="Некорректный email. Запросите электронную почту ещё раз.",
        )

    # ------------------------------------------------------------------
    # 2) Вызов CRM-слоя: он уже возвращает Payload[str], просто прокидываем
    # ------------------------------------------------------------------
    try:
        return await go_update_client_info(
            user_id=user_id,
            channel_id=channel_id,
            parent_name=parent_name,
            phone=phone,
            email=email,
            child_name=child_name,
            child_date_of_birth=child_date_of_birth,
            contact_reason=contact_reason,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # На всякий случай: если CRM-слой неожиданно упал исключением,
        # MCP-tool всё равно возвращает корректный Payload.
        logger.exception("[update_client_info] unexpected error: %s", exc)
        return err(
            code="unexpected_error",
            error="Не удалось сохранить анкету. Попробуйте позже.",
        )
