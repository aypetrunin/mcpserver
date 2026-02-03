"""Модуль поиска свободных слотов по мастерам.

Поиск ведется через API CRM gateway (CRM_BASE_URL).
"""

import asyncio
import logging
import httpx

from datetime import datetime
from typing import Any


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
# Настройка логгера
logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(CRM_HTTP_RETRIES),
    wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def avaliable_time_for_master_list_async(
    date: str,
    service_id: str,
    service_name: str,
    count_slots: int = 30,
    timeout: float = CRM_HTTP_TIMEOUT_S,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Асинхронный запрос на получение доступных слотов по мастерам для указанной услуги.

    :param date: Дата в формате 'YYYY-MM-DD' (на будущее — может использоваться на бэкенде).
    :param service_id: ID услуги, например "1-20347221".
    :param count_slots: Максимальное количество слотов на мастера.
    :param timeout: Таймаут запроса в секундах.
    :return: Список словарей с информацией о мастерах и их слотах.
    """
    logger.info("===crm_avaliable_time_for_master_list===")

    if not service_id or not isinstance(service_id, str):
        logger.warning("Не верный service_id: %s", service_id)
        return [], []

    try:
        input_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        logger.warning(f"Неверный формат даты: {date}. Ожидается 'YYYY-MM-DD'")
        return [{"success": False, "error": f"Неверный формат даты: {date}. Ожидается 'YYYY-MM-DD'"}], []

    today = datetime.now().date()
    if input_date < today:
        logger.warning("Ошибка в выборе даты. Нельзя записаться на прошедшее число: %s", date)
        return [
            {"success": False,
             "error": f"Ошибка в выборе даты. Нельзя записаться на прошедшее число. Напомню, сегодня {today.strftime('%Y-%m-%d')}"}
        ], []

    url = f"{CRM_BASE_URL}/appointments/yclients/product"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info("Отправка запроса на API %s c service_id=%s на дату=%s", url, service_id, date)
            response = await client.post(
                url=url,
                json={"service_id": service_id, "base_date": date},
            )
            response.raise_for_status()
            resp_json = response.json()

    except Exception as e:
        logger.exception("Ошибка API для service_id=%s: %s", service_id, e)
        return [], []

    # Обработка успешного ответа
    if not resp_json.get("success"):
        logger.warning("API вернуло success=False для service_id=%s", service_id)
        return [], []

    # Одиночная услуга
    service_obj = resp_json.get("result", {}).get("service")
    if service_obj and isinstance(service_obj, dict):
        staff_list = service_obj.get("staff", [])
        product_name = service_name.split(',')[0]
        sequences_list = [
            {
                "master_name": item["name"],
                "master_id": item["id"],
                "master_slots": sorted(
                    item.get("dates", []),
                    key=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M")
                    )[:count_slots],
            }
            for item in staff_list if isinstance(item.get("dates"), list)
        ]
        sequences_list = filter_sequences_list(product_name, sequences_list)
        sequences_list = filter_future_slots(sequences_list)
        return sequences_list, []

    # Комплекс
    resp_json_modify  = update_services_in_sequences(resp_json)
    avaliable_sequences = resp_json_modify.get("result", {}).get("avaliable_sequences")
    if avaliable_sequences and isinstance(avaliable_sequences, list):
        # Список для выбора времени.
        sequences_list = [
            {'sequence_id': seq['sequence_id'], 'start_time': seq['total_start_time']}
            for seq in avaliable_sequences
        ]
        # Список комплекса по которому нужно записать отдельно услуги.
        avaliable_sequences_short_list = avaliable_sequences_short(avaliable_sequences)
        return sequences_list, avaliable_sequences_short_list

    return [], []


def update_services_in_sequences(data: dict[str, Any]) -> dict[str, Any]:
    """Функция замены/согласования в словаре услуг названий на используемые в dikidi."""
    replacements = {
        '2950601': {'master_id': '881127', 'master_name': 'Термотерапия'},
        '2950597': {'master_id': '864147', 'master_name': 'Прессотерапия'},
        '2950609': {'master_id': '914499', 'master_name': 'Ролик'},
        '2950603': {'master_id': '914503', 'master_name': 'Токовые Процедуры'}
    }
    # Оригинальная структура с доступом к avaliable_sequences
    for seq in data['result']['avaliable_sequences']:
        for step in seq['steps']:
            rid = step['service_id']
            if rid in replacements:
                step['master_id'] = replacements[rid]['master_id']
                step['master_name'] = replacements[rid]['master_name']
    return data

def avaliable_sequences_short(avaliable_sequences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Получение из полного списка данных укороченного списка достаточного для записи на услуги."""
    result = [
        {
            'sequence_id': seq['sequence_id'],
            'start_time': seq['total_start_time'],
            'services': [
                {
                    'product_id': '7-' + step['service_id'],
                    'master_id': step['master_id'],
                    'master_name': step['master_name'],
                    'date_time': step['start_time']
                }
                for step in seq['steps']
            ]
        }
        for seq in avaliable_sequences
    ]
    return result

def filter_sequences_list(
    name: str,
    sequences_list: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Функция фильтации списка по названию услуги."""
    map_name = {
        "Прессотерапия": "Прессотерапия",
        "Роликовый массажер": "Ролик",
        "Термотерапия": "Термотерапия",
        "Электролиполиз": "Токовые Процедуры",
        "Электромиостимуляция": "Токовые Процедуры",
    }
    filter = [item for item in sequences_list if item['master_name']==map_name.get(name)]
    return filter


def filter_future_slots(
    masters_data: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Фильтрует слоты мастеров, оставляя только будущие. НЕ изменяет исходные данные."""
    now = datetime.now()
    
    result = []
    for master in masters_data:
        filtered_slots = [
            slot for slot in master['master_slots']
            if datetime.strptime(slot, '%Y-%m-%d %H:%M') > now
        ]
        
        # Создаем новую структуру с отфильтрованными слотами
        result.append({
            "master_name": master["master_name"],
            "master_id": master["master_id"],
            "master_slots": filtered_slots  # Только будущие слоты
        })

    return result



# Пример использования
if __name__ == "__main__":
    """Тестовый пример работы функции."""

    async def main() -> None:
        """Тестовый пример работы функции."""
        date = "2025-11-29"
        # service_id = "1-19501163"
        service_id = "7-2950601"
        service_name = "7-2950601"
        # service_id = "7-2950601, 7-2950603"
        logger.info("Доступные мастера:")
        result = await avaliable_time_for_master_list_async(date=date, service_id=service_id, service_name=service_name)
        logger.info(result)

    asyncio.run(main())

# cd /home/copilot_superuser/petrunin/zena
# uv run python -m mcpserver.src.crm.avaliable_time_for_master