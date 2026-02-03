"""
history_httpservice.py

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
"""

from __future__ import annotations

import logging
from typing import TypedDict, Any

import httpx

from src.clients import get_http
from src.http_retry import CRM_HTTP_RETRY
from src.settings import get_settings

logger = logging.getLogger(__name__)

# Читаем settings один раз на модуль.
# Это нормально в вашем проекте, т.к. init_runtime() гарантированно вызывается раньше в main.
S = get_settings()

# Путь endpoint-а (это "часть протокола", а не часть окружения)
HISTORY_OUTGOING_PATH = "/v1/telegram/n8n/outgoing"

# Итоговый URL строим через settings, чтобы домен можно было менять через env.
URL_OUTGOING = URL_OUTGOING = f"{S.CRM_BASE_URL.rstrip('/')}{HISTORY_OUTGOING_PATH}"

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

    Мы оставляем большую сигнатуру, чтобы не менять код во всём проекте.
    Внутри собираем payload и передаём в низкоуровневую функцию отправки.
    """
    # защита от mutable default arguments
    tokens = tokens or {}
    tools = tools or []
    tools_args = tools_args or {}
    tools_result = tools_result or {}

    payload: HttpServiceAdministratorPayload  = {
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
        return {"success": False, "error": f"status={e.response.status_code}", "details": e.response.text[:500]}
    except httpx.RequestError as e:
        logger.warning("httpservice request error: %s", str(e))
        return {"success": False, "error": "network_error", "details": str(e)}


@CRM_HTTP_RETRY
async def _call_administrator_payload(payload: HttpServiceAdministratorPayload) -> None:
    """
    Низкоуровневая функция, которая реально делает HTTP запрос.

    Почему retry здесь?
    -------------------
    Декоратор @CRM_HTTP_RETRY будет повторять запросы только при временных проблемах:
    - timeout / network error
    - HTTP 429
    - HTTP 5xx

    Если ошибка "логическая" (например 401/403/404/400) — retry не делается.
    """
    logger.info("httpservice_call_administator.call_administator")
    
    client = get_http()

    # Если когда-нибудь решите передавать токен через заголовок:
    # headers = {"Authorization": f"Bearer {payload['access_token']}", "Accept": "application/json"}
    # Но сейчас ваш API принимает access_token в JSON — поэтому headers не нужны.

    resp = await client.post(
        URL_OUTGOING,
        json=payload,
        # Таймаут берём из settings (единый стандарт).
        timeout=httpx.Timeout(S.CRM_HTTP_TIMEOUT_S),
    )
    resp.raise_for_status()
    return None
