# src/crm/crm_delete_client_record.py
from __future__ import annotations

"""
Удаление записи клиента.

Что исправлено относительно старой версии:
-----------------------------------------
1) Убрали S = get_settings() на уровне модуля.
   Раньше это читало env при импорте модуля — могло ломаться, если init_runtime()
   ещё не вызывался (тесты, скрипты, другой entrypoint).

2) Убрали URL_DELETE_RECORDS как глобальную константу, построенную из settings.
   Теперь URL строится лениво (в момент реального запроса) через crm_url().

3) Таймаут берём единообразно через crm_timeout_s():
   - если где-то захотят прокинуть свой timeout — это будет просто,
   - сейчас используем стандартный таймаут из settings.
"""

import logging
from typing import Any, Optional, TypedDict

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url

logger = logging.getLogger(__name__.split('.')[-1])

# Относительный путь CRM-метода (безопасная константа, не зависит от env)
DELETE_RECORDS_PATH = "/appointments/client/records/delete"


class DeleteClientRecordPayload(TypedDict):
    user_companychat: int
    channel_id: int
    record_id: int


class DeleteClientRecordResponse(TypedDict):
    success: bool
    data: str
    error: Optional[str]


async def delete_client_record(user_companychat: int, office_id: int, record_id: int) -> DeleteClientRecordResponse:
    """
    Удаление записи на услугу.

    Важно:
    - office_id в старом коде фактически является channel_id.
      Сохраняем сигнатуру, чтобы не менять вызовы во всём проекте.

    Возвращает:
    - {"success": True,  "data": "...", "error": None} — если CRM подтвердил удаление
    - {"success": False, "data": "...", "error": "..."} — если ошибка/не найдено
    """

    payload: DeleteClientRecordPayload = {
        "user_companychat": user_companychat,
        "channel_id": office_id,
        "record_id": record_id,
    }

    try:
        resp_json = await _delete_client_record_payload(payload)

        # CRM возвращает dict с success (и иногда доп. полями)
        if isinstance(resp_json, dict) and resp_json.get("success") is True:
            return {
                "success": True,
                "data": f"Запись payload={payload} - удалена",
                "error": None,
            }

        # если CRM ответил success=False (или без success)
        return {
            "success": False,
            "data": f"Запись payload={payload} - не существует",
            "error": None,
        }

    except httpx.HTTPStatusError as e:
        # Сюда попадём, если ретраи исчерпаны или статус неретраибельный (4xx кроме 429)
        logger.warning(
            "crm_delete_client_record http error status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return {"success": False, "data": "", "error": f"status={e.response.status_code}"}

    except httpx.RequestError as e:
        # Сюда попадём, если ретраи исчерпаны по сетевым ошибкам
        logger.warning("crm_delete_client_record request error: %s", str(e))
        return {"success": False, "data": "", "error": "network_error"}

    except ValueError as e:
        # например: invalid json
        logger.error("crm_delete_client_record bad response payload=%s: %s", payload, e)
        return {"success": False, "data": "", "error": "invalid_response"}

    except Exception as e:  # noqa: BLE001
        logger.exception("crm_delete_client_record unexpected error payload=%s: %s", payload, e)
        return {"success": False, "data": "", "error": "unexpected_error"}


@CRM_HTTP_RETRY
async def _delete_client_record_payload(payload: DeleteClientRecordPayload) -> dict[str, Any]:
    """
    Низкоуровневый HTTP-вызов с единым retry-поведением:
    - timeout / network error
    - HTTP 429
    - HTTP 5xx

    Здесь мы держим "чистый" HTTP-слой:
    - строим URL лениво через crm_url()
    - берём таймаут лениво через crm_timeout_s()
    """
    client = get_http()

    url = crm_url(DELETE_RECORDS_PATH)
    timeout_s = crm_timeout_s(0.0)

    resp = await client.post(
        url,
        json=payload,
        timeout=httpx.Timeout(timeout_s),
    )
    resp.raise_for_status()

    try:
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Недопустимый ответ JSON от CRM: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Неожиданный тип JSON из CRM: {type(data)}")

    return data


# import logging
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


# @retry(
#     stop=stop_after_attempt(CRM_HTTP_RETRIES),
#     wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
#     retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
#     reraise=True,
# )
# async def delete_client_record(user_companychat: int, office_id: int, record_id: int) -> dict:
#     """Удаление записи на услугу."""
#     logger.info("===crm.crm_delete_client_record===")

#     endpoint_url = f"{CRM_BASE_URL}/appointments/client/records/delete"

#     try:
#         payload = {
#             "user_companychat": user_companychat,
#             "channel_id": office_id,
#             "record_id": record_id,
#         }

#         async with httpx.AsyncClient(timeout=CRM_HTTP_TIMEOUT_S) as client:
#             logger.info("Отправка запроса на удаление %s с payload=%s", endpoint_url, payload)
#             response = await client.post(endpoint_url, json=payload)
#             response.raise_for_status()

#             try:
#                 r = response.json()
#                 if r.get('success'):
#                     return {'success': True, 'data': f'Запись payload={payload} - удалена'}
#                 else:
#                     return {'success': False, 'data': f'Запись payload={payload} - не существует'}
 
#             except ValueError as e:
#                 logger.error("Сервер вернул не-JSON при удалении. payload=%s: %s", payload, e)
#                 return {"success": False, "data": [], "error": "Ответ сервера не в формате JSON"}

#     except httpx.TimeoutException as e:
#         logger.error("Таймаут при удалении с payload=%s: %s", payload, e)
#         raise  # tenacity retry

#     except httpx.HTTPStatusError as e:
#         logger.error(
#             "Ошибка HTTP %d при удалении с payload=%s: %s",
#             e.response.status_code,
#             payload,
#             e,
#         )
#         return {"success": False, "data": [], "error": f"HTTP ошибка: {e.response.status_code}"}

#     except Exception as e:
#         logger.exception("Неожиданная ошибка при удалении с payload=%s: %s", payload, e)
#         return {"success": False, "data": [], "error": "Неизвестная ошибка при удалении"}
