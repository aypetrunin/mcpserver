"""
httpservice_call_administrator.py

Назначение (для новичка)
========================
Этот модуль отправляет "историю/контекст диалога" на endpoint сервиса
httpservice.ai2b.pro.

Почему мы НЕ создаём http-клиент внутри функции?
------------------------------------------------
Раньше можно было делать так:
    async with httpx.AsyncClient(...) as client:
        await client.post(...)

Но это плохо, если запросов много:
- клиент создаётся заново каждый раз (дорого)
- соединения (keep-alive) не переиспользуются
- сложнее корректно закрывать ресурсы

Правильный подход:
------------------
1) Мы создаём общий httpx.AsyncClient ОДИН раз при старте процесса:
      await init_clients()
   (в main_v2.py)

2) Потом в любом месте берём общий клиент:
      client = get_http()

3) На shutdown закрываем клиента ОДИН раз:
      await close_clients()

Зачем retry?
------------
Иногда бывают временные проблемы:
- сеть/таймаут
- 429 Too Many Requests
- 5xx ошибки сервера

В этих случаях полезно повторить запрос.

Мы используем стандартный retry из src/http_retry.py:
- параметры берутся из settings.py (env)
- поведение единое для всего проекта

Отправляет "историю/контекст диалога" на endpoint сервиса.
- HTTP клиент берём из src.clients.get_http()
- retry через @CRM_HTTP_RETRY
- settings/env читаем ЛЕНИВО (важно для init_runtime())
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

import httpx

from src.clients import get_http
from src.http_retry import CRM_HTTP_RETRY
from src.settings import get_settings

logger = logging.getLogger(__name__)

HISTORY_OUTGOING_PATH = "/v1/telegram/n8n/outgoing"


def outgoing_url() -> str:
    """
    Ленивая сборка URL, чтобы settings/env читались только при реальном вызове функции,
    а не на импорте модуля.
    """
    s = get_settings()
    return f"{s.CRM_BASE_URL.rstrip('/')}{HISTORY_OUTGOING_PATH}"


def crm_timeout_s() -> float:
    """
    Ленивая вычитка таймаута из settings (единый стандарт).
    """
    return float(get_settings().CRM_HTTP_TIMEOUT_S)


class HttpServiceAdministratorPayload(TypedDict):
    user_id: int
    user_companychat: int
    reply_to_history_id: int
    access_token: str
    text: str
    tokens: dict[str, Any]
    tools: list[str]
    tools_args: dict[str, Any]
    tools_result: dict[str, Any]
    prompt_system: str
    template_prompt_system: str
    dialog_state: str
    dialog_state_new: str
    call_manager: bool


async def httpservice_call_administrator(
    user_id: int,
    user_companychat: int,
    reply_to_history_id: int,
    access_token: str,
    text: str = "Клиент просит администратора.",
    tokens: dict[str, Any] | None = None,
    tools: list[str] | None = None,
    tools_args: dict[str, Any] | None = None,
    tools_result: dict[str, Any] | None = None,
    prompt_system: str = "",
    template_prompt_system: str = "",
    dialog_state: str = "",
    dialog_state_new: str = "",
    call_manager: bool = True,
) -> dict[str, Any]:
    """
    Публичная функция.

    Сигнатуру оставляем широкой для совместимости.
    Внутри собираем payload и отправляем в низкоуровневую функцию.
    """
    logger.info("httpservice_call_administrator")

    # защита от mutable default arguments
    tokens = tokens or {}
    tools = tools or []
    tools_args = tools_args or {}
    tools_result = tools_result or {}

    payload: HttpServiceAdministratorPayload = {
        "user_id": user_id,
        "user_companychat": user_companychat,
        "reply_to_history_id": reply_to_history_id,
        "access_token": access_token,
        "text": text,
        "tokens": tokens,
        "tools": tools,
        "tools_args": tools_args,
        "tools_result": tools_result,
        "prompt_system": prompt_system,
        "template_prompt_system": template_prompt_system,
        "dialog_state": dialog_state,
        "dialog_state_new": dialog_state_new,
        "call_manager": call_manager,
    }

    try:
        await _call_administrator_payload(payload)
        return {"success": True, "data": "Администратор вызван."}

    except httpx.HTTPStatusError as e:
        logger.warning(
            "httpservice http error status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return {
            "success": False,
            "error": f"status={e.response.status_code}",
            "details": e.response.text[:500],
        }

    except httpx.RequestError as e:
        logger.warning("httpservice request error: %s", str(e))
        return {"success": False, "error": "network_error", "details": str(e)}


@CRM_HTTP_RETRY
async def _call_administrator_payload(payload: HttpServiceAdministratorPayload) -> None:
    """
    Низкоуровневая функция, которая реально делает HTTP запрос.
    Retry применяется только к временным проблемам (timeout/network/429/5xx).
    """
    client = get_http()

    resp = await client.post(
        outgoing_url(),
        json=payload,
        timeout=httpx.Timeout(crm_timeout_s()),
    )
    resp.raise_for_status()
