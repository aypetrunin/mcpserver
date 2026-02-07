# httpservice_call_administrator.py
"""Вызов администратора через httpservice.ai2b.pro.

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
1) Мы создаём общий httpx.AsyncClient один раз при старте процесса:
      await init_clients()
   (в main_v2.py)

2) Потом в любом месте берём общий клиент:
      client = get_http()

3) На shutdown закрываем клиента один раз:
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
- settings/env читаем лениво (важно для init_runtime())
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TypedDict

import httpx

from src.clients import get_http
from src.http_retry import CRM_HTTP_RETRY
from src.settings import get_settings
from src.crm._crm_result import Payload, ok, err  # поправь путь, если модуль лежит иначе

logger = logging.getLogger(__name__)

HISTORY_OUTGOING_PATH = "/v1/telegram/n8n/outgoing"


def outgoing_url() -> str:
    """Возвращает полный URL endpoint для отправки исходящей истории."""
    s = get_settings()
    return f"{s.CRM_BASE_URL.rstrip('/')}{HISTORY_OUTGOING_PATH}"


def crm_timeout_s() -> float:
    """Возвращает таймаут HTTP-запросов к CRM в секундах."""
    return float(get_settings().CRM_HTTP_TIMEOUT_S)


class HttpServiceAdministratorPayload(TypedDict):
    """Payload запроса на вызов администратора."""

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


def _code_from_status(status: int) -> str:
    """Нормализуем HTTP статус в короткий код ошибки."""
    if status in (401, 403):
        return "unauthorized"
    if status == 404:
        return "not_found"
    if status == 409:
        return "conflict"
    if status == 422:
        return "validation_error"
    if status == 429:
        return "rate_limited"
    if 500 <= status <= 599:
        return "crm_unavailable"
    return "crm_error"


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
) -> Payload[str]:
    """Отправляет запрос на вызов администратора через httpservice.

    Возвращает ТОЛЬКО единый контракт:
    - ok("Администратор вызван.") при успехе
    - err(code=..., error="...") при ошибке
    """
    logger.info("httpservice_call_administrator")

    payload: HttpServiceAdministratorPayload = {
        "user_id": user_id,
        "user_companychat": user_companychat,
        "reply_to_history_id": reply_to_history_id,
        "access_token": access_token,
        "text": text,
        "tokens": tokens or {},
        "tools": tools or [],
        "tools_args": tools_args or {},
        "tools_result": tools_result or {},
        "prompt_system": prompt_system,
        "template_prompt_system": template_prompt_system,
        "dialog_state": dialog_state,
        "dialog_state_new": dialog_state_new,
        "call_manager": call_manager,
    }

    try:
        await _call_administrator_payload(payload)
        return ok("Администратор вызван.")

    except asyncio.CancelledError:
        # важно не превращать CancelledError в err (иначе ломается shutdown)
        raise

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        body_snippet = (exc.response.text or "")[:500]

        # детали оставляем в логах (контракт err не содержит details)
        logger.warning(
            "httpservice http error status=%s body=%s",
            status,
            body_snippet,
        )
        return err(code=_code_from_status(status), error=f"HTTP {status} from httpservice")

    except httpx.RequestError as exc:
        logger.warning("httpservice request error: %s", exc)
        return err(code="network_error", error="Network error while calling httpservice")

    except Exception as exc:
        logger.exception("unexpected error in httpservice_call_administrator: %s", exc)
        return err(code="internal_error", error="Unexpected error")


@CRM_HTTP_RETRY
async def _call_administrator_payload(payload: HttpServiceAdministratorPayload) -> None:
    """Отправляет payload на endpoint httpservice.

    Retry применяется только к временным проблемам (timeout/network/429/5xx).
    """
    client = get_http()

    resp = await client.post(
        outgoing_url(),
        json=payload,
        timeout=httpx.Timeout(crm_timeout_s()),
    )
    resp.raise_for_status()
