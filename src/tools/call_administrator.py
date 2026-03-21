"""MCP-сервер для вызова администратора.

Action-tool: эскалация диалога и вызов администратора в CRM.
Единый контракт ответов: Payload (ok/err).
"""

from __future__ import annotations

import asyncio
import logging

from fastmcp import FastMCP

from src.crm._crm_result import Payload, err

from ..request.httpservice_call_administrator import (
    httpservice_call_administrator,  # type: ignore
)


logger = logging.getLogger(__name__)

tool_call_administrator = FastMCP(name="call_administrator")


@tool_call_administrator.tool(
    name="call_administrator",
    description=(
        "Вызов администратора.\n\n"
        "**Назначение:**\n"
        "Используется, когда клиент хочет вызвать администратора или когда по контексту диалога "
        "клиент недоволен общением с ИИ-помощником.\n\n"
        "**Примеры вопросов:**\n"
        "- Позови администратора.\n"
        "- Ты делаешь всё неправильно и не понимаешь меня.\n"
        "- Всё не так, ты ничего не умеешь!\n\n"
        "**Args:**\n"
        "- `user_companychat` (`str`, required): ID клиент-чата.\n"
        "- `user_id` (`str`, required): ID клиента.\n"
        "- `reply_to_history_id` (`str`, required): ID сообщения.\n"
        "- `access_token` (`str`, required): Токен доступа.\n\n"
        "**Returns:**\n"
        "- Payload[str]\n"
    ),
)
async def call_administrator(
    user_companychat: str,
    user_id: str,
    reply_to_history_id: str,
    access_token: str,
) -> Payload[str]:
    """Вызвать администратора в CRM (fail-fast + единый контракт)."""
    # ------------------------------------------------------------------
    # 1) Fail-fast: валидация идентификаторов
    # ------------------------------------------------------------------
    try:
        companychat_id = int(user_companychat)
        user_id_int = int(user_id)
        reply_id = int(reply_to_history_id)
    except (TypeError, ValueError):
        return err(
            code="validation_error",
            error=(
                "Некорректные параметры: "
                "user_companychat, user_id и reply_to_history_id должны быть числами."
            ),
        )

    if not access_token or not isinstance(access_token, str):
        return err(
            code="validation_error",
            error="access_token не задан или имеет неверный формат.",
        )

    # ------------------------------------------------------------------
    # 2) CRM-вызов: httpservice_call_administrator возвращает Payload[str]
    # ------------------------------------------------------------------
    try:
        return await httpservice_call_administrator(
            user_companychat=companychat_id,
            user_id=user_id_int,
            reply_to_history_id=reply_id,
            access_token=access_token,
        )
    except asyncio.CancelledError:
        # корректный shutdown / cancel
        raise
    except Exception as exc:
        # фолбэк на неожиданные ошибки
        logger.exception("[call_administrator] unexpected error: %s", exc)
        return err(
            code="unexpected_error",
            error="Не удалось вызвать администратора. Попробуйте позже.",
        )
