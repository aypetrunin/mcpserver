"""Регистрирует нового клиента в GO CRM."""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url


logger = logging.getLogger(__name__.split(".")[-1])

CREATE_CLIENT_PATH = "/appointments/go_crm/create_client"


class ErrorResponse(TypedDict):
    """Описывает ответ с ошибкой."""

    success: Literal[False]
    error: str


class SuccessResponse(TypedDict):
    """Описывает успешный ответ."""

    success: Literal[True]
    message: str


ResponsePayload = ErrorResponse | SuccessResponse


def _log_and_build_input_error(param_name: str, value: Any) -> ErrorResponse:
    """Логирует и возвращает ошибку валидации входных данных."""
    logger.warning("Не указан или неверный тип '%s': %r", param_name, value)
    return ErrorResponse(
        success=False,
        error="Ошибка в типах входных данных. Проверь и перезапусти инструмент.",
    )


def _validate_str_param(value: Any) -> bool:
    """Проверяет, что значение является непустой строкой."""
    return isinstance(value, str) and bool(value.strip())


@CRM_HTTP_RETRY
async def _create_client_payload(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    """Выполняет запрос создания клиента и возвращает JSON."""
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
    """Создаёт клиента в GO CRM."""
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
        if not _validate_str_param(value):
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
        logger.warning("go_update_client_info request error payload=%s: %s", payload, e)
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

    except Exception as e:
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
