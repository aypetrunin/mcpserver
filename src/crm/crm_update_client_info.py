"""Модуль переноса урока клиента."""

from __future__ import annotations


import asyncio
import logging
from typing import Any, Literal, TypedDict, cast, Optional
from datetime import datetime

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)



class ErrorResponse(TypedDict):
    success: Literal[False]
    error: str


class SuccessResponse(TypedDict):
    success: Literal[True]
    message: str


ResponsePayload = ErrorResponse | SuccessResponse


def _log_and_build_input_error(param_name: str, value: Any) -> ErrorResponse:
    logger.warning(
        "Не указан или неверный тип '%s': %r",
        param_name,
        value,
    )
    return ErrorResponse(
        success=False,
        error=(
            "Ошибка в типах входных данных. "
            "Проверь и перезапусти инструмент."
        ),
    )


def _validate_str_param(name: str, value: Any) -> bool:
    return isinstance(value, str) and bool(value)


BASE_URL: str = "https://httpservice.ai2b.pro"
TIMEOUT_SECONDS: float = 180.0
MAX_RETRIES: int = 1


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def go_update_client_info(
    user_id: str,
    channel_id: str,
    parent_name: str,
    phone: str,
    email: str,
    child_name: str,
    child_date_of_birth: str,
    contact_reason: str,
    timeout: float = TIMEOUT_SECONDS,
) -> ResponsePayload:
    """Регистрация нового клиента в GO GRM."""

    logger.info("===crm_go.go_update_client_info===")

    for name, value in (
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


    url = f"{BASE_URL}/appointments/go_crm/create_client"

    payload: dict[str, str] = {
        "user_id": user_id,
        "channel_id": channel_id,
        "parent_fio": parent_name,
        "phone": phone,
        "mail": email,
        "child_fio": child_name,
        "birthday": child_date_of_birth,
        "comment": f"Создан через API. Причина обращения: {contact_reason}"
    }

    logger.info("Отправка запроса на %s с payload=%r", url, payload)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url=url, json=payload)
            response.raise_for_status()
            resp_json: dict[str, Any] = response.json()

    except (httpx.TimeoutException, httpx.ConnectError) as e:
        msg = f"Сетевая ошибка при запросе на {url} с payload={payload!r}: {e}"
        logger.exception(msg)
        return ErrorResponse(success=False, error={"message":msg})
    
    except httpx.HTTPError as e:
        msg = f"HTTP-ошибка при запросе на {url} с payload={payload!r}: {e}"
        logger.exception(msg)
        return ErrorResponse(success=False, error={"message":msg})

    except Exception as e:  # noqa: BLE001
        msg = f"Неожиданная при запросе на {url} с payload={payload!r}: {e}"
        logger.exception(msg)
        return ErrorResponse(success=False, error={"message":msg})

    logger.info(f"resp_json: {resp_json}")

    if not resp_json.get("success"):
        msg = "Ошибка создания ноаого клиента в GO CRM. Обратитесь к администратору."
        logger.exception(msg)
        return ErrorResponse(success=False, error={"message":msg})

    return SuccessResponse(
        success=True,
        message=f"Ваши данные сохранены. С вами скоро свяжется администратор.",
    )
