"""MCP-сервер для вызова администратора."""

from typing import Any

from fastmcp import FastMCP

from ..request.httpservice_call_administrator import (
    httpservice_call_administrator,  # type: ignore
)


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
        "- `user_companychat` (`str`, required): ID клиент-чат.\n"
        "- `user_id` (`str`, required): ID клиента.\n"
        "- `reply_to_history_id` (`str`, required): ID сообщения.\n"
        "- `access_token` (`str`, required): токен доступа.\n\n"
        "**Returns:**\n"
        "- `dict`\n"
    ),
)
async def call_administrator(
    user_companychat: str,
    user_id: str,
    reply_to_history_id: str,
    access_token: str,
) -> dict[str, Any]:
    """Вызвать администратора в CRM."""
    try:
        return await httpservice_call_administrator(
            user_companychat=int(user_companychat),
            user_id=int(user_id),
            reply_to_history_id=int(reply_to_history_id),
            access_token=access_token,
        )
    except ValueError:
        return {"success": False, "data": "Ошибка вызова администратора."}

