# src/crm/crm_update_client_info.py
"""
Mодуль регистрации нового клиента в GO CRM.

Что исправлено относительно старой версии:
-----------------------------------------
1) Убрали S = get_settings() на уровне модуля.
   Раньше settings читались при импорте файла → могло ломаться, если init_runtime()
   ещё не вызывался (тесты/скрипты/другой entrypoint).

2) Убрали URL_CREATE_CLIENT как глобальную константу, построенную из settings.
   Теперь URL строим лениво в момент HTTP-вызова через crm_url().

3) Таймаут берём единообразно через crm_timeout_s():
   - если timeout > 0 — используем его
   - иначе берём settings.CRM_HTTP_TIMEOUT_S (лениво)

Формат ответов (ErrorResponse/SuccessResponse) и бизнес-логика сохранены.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict

import httpx

from src.clients import get_http
from src.http_retry import CRM_HTTP_RETRY
from src.crm.crm_http import crm_timeout_s, crm_url

logger = logging.getLogger(__name__)

# Относительный путь к методу GO CRM (безопасная константа)
CREATE_CLIENT_PATH = "/appointments/go_crm/create_client"


class ErrorResponse(TypedDict):
    success: Literal[False]
    error: str


class SuccessResponse(TypedDict):
    success: Literal[True]
    message: str


ResponsePayload = ErrorResponse | SuccessResponse


def _log_and_build_input_error(param_name: str, value: Any) -> ErrorResponse:
    """Единая форма ошибки на неверных входных параметрах."""
    logger.warning("Не указан или неверный тип '%s': %r", param_name, value)
    return ErrorResponse(
        success=False,
        error="Ошибка в типах входных данных. Проверь и перезапусти инструмент.",
    )


def _validate_str_param(name: str, value: Any) -> bool:
    """True только для непустой строки."""
    return isinstance(value, str) and bool(value.strip())


@CRM_HTTP_RETRY
async def _create_client_payload(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    """
    Низкоуровневый HTTP-вызов с единым retry-поведением:
    - timeout / network error
    - HTTP 429
    - HTTP 5xx

    Важно:
    - URL строим лениво через crm_url(CREATE_CLIENT_PATH),
      поэтому settings не читаются при импорте модуля.
    """
    client = get_http()
    url = crm_url(CREATE_CLIENT_PATH)

    resp = await client.post(
        url,
        json=payload,
        timeout=httpx.Timeout(timeout_s),
    )
    resp.raise_for_status()

    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Неожиданный тип JSON из CRM: {type(data)}")
    return data


async def go_update_client_info(
    user_id: str,
    channel_id: str,
    parent_name: str,
    phone: str,
    email: str,
    child_name: str,
    child_date_of_birth: str,
    contact_reason: str,
    timeout: float = 0.0,
) -> ResponsePayload:
    """
    Регистрация нового клиента в GO CRM.

    Параметры:
    - timeout: если >0 — используем его, иначе берём settings.CRM_HTTP_TIMEOUT_S (лениво)
    """
    logger.info("=== crm_go.go_update_client_info ===")

    # В текущем файле user_id не валидировался, хотя он обязателен в payload.
    # Оставляем строгую проверку, чтобы не отправлять мусор в CRM.
    for name, value in (
        ("user_id", user_id),
        ("channel_id", channel_id),
        ("parent_name", parent_name),
        ("phone", phone),
        ("email", email),
        ("child_name", child_name),
        ("child_date_of_birth", child_date_of_birth),
        ("contact_reason", contact_reason),
    ):
        if not _validate_str_param(name, value):
            return _log_and_build_input_error(name, value)

    payload: dict[str, str] = {
        "user_id": user_id.strip(),
        "channel_id": channel_id.strip(),
        "parent_fio": parent_name.strip(),
        "phone": phone.strip(),
        "mail": email.strip(),
        "child_fio": child_name.strip(),
        "birthday": child_date_of_birth.strip(),
        "comment": f"Создан через API. Причина обращения: {contact_reason.strip()}",
    }

    effective_timeout = crm_timeout_s(timeout)

    try:
        resp_json = await _create_client_payload(payload=payload, timeout_s=effective_timeout)
        logger.info("go_update_client_info resp_json=%s", resp_json)

    except httpx.HTTPStatusError as e:
        logger.warning(
            "go_update_client_info http error status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return ErrorResponse(
            success=False,
            error="Сервис GO CRM временно недоступен. Обратитесь к администратору.",
        )

    except httpx.RequestError as e:
        logger.warning("go_update_client_info request error payload=%s: %s", payload, str(e))
        return ErrorResponse(
            success=False,
            error="Сетевая ошибка при обращении к GO CRM. Обратитесь к администратору.",
        )

    except ValueError:
        logger.exception("go_update_client_info invalid json payload=%s", payload)
        return ErrorResponse(
            success=False,
            error="GO CRM вернул некорректный ответ. Обратитесь к администратору.",
        )

    except Exception as e:  # noqa: BLE001
        logger.exception("go_update_client_info unexpected error payload=%s: %s", payload, e)
        return ErrorResponse(
            success=False,
            error="Неизвестная ошибка при обращении к GO CRM. Обратитесь к администратору.",
        )

    if resp_json.get("success") is not True:
        return ErrorResponse(
            success=False,
            error="Ошибка создания нового клиента в GO CRM. Обратитесь к администратору.",
        )

    return SuccessResponse(
        success=True,
        message="Ваши данные сохранены. С вами скоро свяжется администратор.",
    )



# """Модуль переноса урока клиента."""

# from __future__ import annotations


# import asyncio
# import logging
# from typing import Any, Literal, TypedDict, cast, Optional
# from datetime import datetime

# import httpx
# from tenacity import (
#     retry,
#     retry_if_exception_type,
#     stop_after_attempt,
#     wait_exponential,
# )
# from .crm_settings import (
#     CRM_BASE_URL,
#     CRM_HTTP_TIMEOUT_S,
#     CRM_HTTP_RETRIES,
#     CRM_RETRY_MIN_DELAY_S,
#     CRM_RETRY_MAX_DELAY_S,
# )

# logger = logging.getLogger(__name__)


# class ErrorResponse(TypedDict):
#     success: Literal[False]
#     error: str


# class SuccessResponse(TypedDict):
#     success: Literal[True]
#     message: str


# ResponsePayload = ErrorResponse | SuccessResponse


# def _log_and_build_input_error(param_name: str, value: Any) -> ErrorResponse:
#     logger.warning(
#         "Не указан или неверный тип '%s': %r",
#         param_name,
#         value,
#     )
#     return ErrorResponse(
#         success=False,
#         error=(
#             "Ошибка в типах входных данных. "
#             "Проверь и перезапусти инструмент."
#         ),
#     )


# def _validate_str_param(name: str, value: Any) -> bool:
#     return isinstance(value, str) and bool(value)


# @retry(
#     stop=stop_after_attempt(CRM_HTTP_RETRIES),
#     wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
#     retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
#     reraise=True,
# )
# async def go_update_client_info(
#     user_id: str,
#     channel_id: str,
#     parent_name: str,
#     phone: str,
#     email: str,
#     child_name: str,
#     child_date_of_birth: str,
#     contact_reason: str,
#     timeout: float = CRM_HTTP_TIMEOUT_S,
# ) -> ResponsePayload:
#     """Регистрация нового клиента в GO GRM."""

#     logger.info("===crm_go.go_update_client_info===")

#     for name, value in (
#         ("channel_id", channel_id),
#         ("parent_name", parent_name),
#         ("phone", phone),
#         ("email", email),
#         ("child_name", child_name),
#         ("child_date_of_birth", child_date_of_birth),
#         ("contact_reason", contact_reason),
#     ):
#         if not _validate_str_param(name, value):
#             return _log_and_build_input_error(name, value)


#     url = f"{CRM_BASE_URL}/appointments/go_crm/create_client"

#     payload: dict[str, str] = {
#         "user_id": user_id,
#         "channel_id": channel_id,
#         "parent_fio": parent_name,
#         "phone": phone,
#         "mail": email,
#         "child_fio": child_name,
#         "birthday": child_date_of_birth,
#         "comment": f"Создан через API. Причина обращения: {contact_reason}"
#     }

#     logger.info("Отправка запроса на %s с payload=%r", url, payload)

#     try:
#         async with httpx.AsyncClient(timeout=timeout) as client:
#             response = await client.post(url=url, json=payload)
#             response.raise_for_status()
#             resp_json: dict[str, Any] = response.json()

#     except (httpx.TimeoutException, httpx.ConnectError) as e:
#         msg = f"Сетевая ошибка при запросе на {url} с payload={payload!r}: {e}"
#         logger.exception(msg)
#         return ErrorResponse(success=False, error={"message":msg})
    
#     except httpx.HTTPError as e:
#         msg = f"HTTP-ошибка при запросе на {url} с payload={payload!r}: {e}"
#         logger.exception(msg)
#         return ErrorResponse(success=False, error={"message":msg})

#     except Exception as e:  # noqa: BLE001
#         msg = f"Неожиданная при запросе на {url} с payload={payload!r}: {e}"
#         logger.exception(msg)
#         return ErrorResponse(success=False, error={"message":msg})

#     logger.info(f"resp_json: {resp_json}")

#     if not resp_json.get("success"):
#         msg = "Ошибка создания ноаого клиента в GO CRM. Обратитесь к администратору."
#         logger.exception(msg)
#         return ErrorResponse(success=False, error={"message":msg})

#     return SuccessResponse(
#         success=True,
#         message=f"Ваши данные сохранены. С вами скоро свяжется администратор.",
#     )
