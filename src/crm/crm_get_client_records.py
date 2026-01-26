# crm_get_client_records.py
import logging
import httpx

from typing import Any, TypedDict, Optional, List, Dict
from datetime import datetime
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .crm_settings import (
    CRM_BASE_URL,
    CRM_HTTP_TIMEOUT_S,
    CRM_HTTP_RETRIES,
    CRM_RETRY_MIN_DELAY_S,
    CRM_RETRY_MAX_DELAY_S,
)

logger = logging.getLogger(__name__)


class PersonalRecord(TypedDict, total=False):
    record_id: int
    record_date: str
    master_id: int
    master_name: str
    product_id: int
    product_name: str


class PersonalRecordsResponse(TypedDict):
    success: bool
    data: List[PersonalRecord]
    error: Optional[str]


@retry(
    stop=stop_after_attempt(CRM_HTTP_RETRIES),
    wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def get_client_records(user_companychat: int, channel_id: str) -> PersonalRecordsResponse:
    """Асинхронный поиск записей клиента через API CRM gateway."""

    logger.info("===crm.crm_get_client_records===")

    endpoint_url = f"{CRM_BASE_URL}/appointments/client/records"
    payload = {"user_companychat": user_companychat, "channel_id": channel_id}

    try:
        async with httpx.AsyncClient(timeout=CRM_HTTP_TIMEOUT_S) as client:
            logger.info("Отправка запроса на поиск %s с payload=%s", endpoint_url, payload)
            response = await client.post(endpoint_url, json=payload)
            response.raise_for_status()
            resp_json = response.json()

        return response_format(resp_json, channel_id)

    except httpx.TimeoutException as e:
        logger.error("Таймаут при поиске с payload=%s: %s", payload, e)
        raise  # tenacity retry

    except httpx.HTTPStatusError as e:
        logger.error(
            "Ошибка HTTP %d при поиске с payload=%s: %s",
            e.response.status_code,
            payload,
            e,
        )
        return {"success": False, "data": [], "error": f"HTTP ошибка: {e.response.status_code}"}

    except Exception as e:
        logger.exception("Неожиданная ошибка при поиске с payload=%s: %s", payload, e)
        return {"success": False, "data": [], "error": "Неизвестная ошибка при поиске"}


def _parse_dt(dt_str: str) -> Optional[datetime]:
    """Пытаемся распарсить дату; возвращаем None если не получилось."""
    if not dt_str:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%d.%m.%Y %H:%M",
        "%d.%m.%y %H:%M",
    ):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def response_format(response: Dict[str, Any], channel_id: str) -> PersonalRecordsResponse:
    if not response.get("success"):
        return {"success": False, "data": [], "error":"Ошибка поиска записей клиента"}

    result: List[PersonalRecord] = []

    for record in response.get("records", []):
        if not record.get("success"):
            continue

        if record.get("status") != "Ожидает...":
            continue

        master = record.get("master_id") or {}
        product = record.get("product") or {}

        rec_date = record.get("date")
        if not rec_date:
            continue  # или оставляйте, но тогда сортировка/вывод должны уметь

        result.append(
            {
                "record_id": record.get("id"),
                "record_date": rec_date,
                "office_id": channel_id,
                "master_id": master.get("id"),
                "master_name": master.get("name"),
                "product_id": product.get("id"),
                "product_name": product.get("name"),
            }
        )

    # сортировка: невалидные даты отправим в конец
    result.sort(key=lambda x: _parse_dt(x.get("record_date", "")) or datetime.max)

    return {"success": True, "data": result}
