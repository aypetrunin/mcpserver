import logging
import httpx

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .crm_settings import (
    CRM_BASE_URL,
    CRM_HTTP_TIMEOUT_S,
    CRM_HTTP_RETRIES,
    CRM_RETRY_MIN_DELAY_S,
    CRM_RETRY_MAX_DELAY_S,
)

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(CRM_HTTP_RETRIES),
    wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def delete_client_record(user_companychat: int, office_id: int, record_id: int) -> dict:
    """Удаление записи на услугу."""
    logger.info("===crm.crm_delete_client_record===")

    endpoint_url = f"{CRM_BASE_URL}/appointments/client/records/delete"

    try:
        payload = {
            "user_companychat": user_companychat,
            "channel_id": office_id,
            "record_id": record_id,
        }

        async with httpx.AsyncClient(timeout=CRM_HTTP_TIMEOUT_S) as client:
            logger.info("Отправка запроса на удаление %s с payload=%s", endpoint_url, payload)
            response = await client.post(endpoint_url, json=payload)
            response.raise_for_status()

            try:
                r = response.json()
                if r.get('success'):
                    return {'success': True, 'data': f'Запись payload={payload} - удалена'}
                else:
                    return {'success': False, 'data': f'Запись payload={payload} - не существует'}
 
            except ValueError as e:
                logger.error("Сервер вернул не-JSON при удалении. payload=%s: %s", payload, e)
                return {"success": False, "data": [], "error": "Ответ сервера не в формате JSON"}

    except httpx.TimeoutException as e:
        logger.error("Таймаут при удалении с payload=%s: %s", payload, e)
        raise  # tenacity retry

    except httpx.HTTPStatusError as e:
        logger.error(
            "Ошибка HTTP %d при удалении с payload=%s: %s",
            e.response.status_code,
            payload,
            e,
        )
        return {"success": False, "data": [], "error": f"HTTP ошибка: {e.response.status_code}"}

    except Exception as e:
        logger.exception("Неожиданная ошибка при удалении с payload=%s: %s", payload, e)
        return {"success": False, "data": [], "error": "Неизвестная ошибка при удалении"}
