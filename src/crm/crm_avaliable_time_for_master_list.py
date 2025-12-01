"""Модуль поиска свободных слотов по мастерам.

Поиск ведется через API https://httpservice.ai2b.pro.
"""

import asyncio
from datetime import datetime
import logging
from typing import Any, Dict, List

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Настройка логгера
logger = logging.getLogger(__name__)

# Константы (лучше вынести в .env или config)
BASE_URL = "https://httpservice.ai2b.pro"
TIMEOUT_SECONDS = 180.0
MAX_RETRIES = 3


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def avaliable_time_for_master_list_async(
    date: str,
    service_id: str,
    servise_name: str = None,
    count_slots: int = 30,
    timeout: float = TIMEOUT_SECONDS,
) -> List[Dict[str, Any]]:
    """Асинхронный запрос на получение доступных слотов по мастерам для указанной услуги.

    :param date: Дата в формате 'YYYY-MM-DD' (на будущее — может использоваться на бэкенде).
    :param service_id: ID услуги, например "1-20347221".
    :param count_slots: Максимальное количество слотов на мастера.
    :param timeout: Таймаут запроса в секундах.
    :return: Список словарей с информацией о мастерах и их слотах.
    """
    logger.info("===crm_avaliable_time_for_master_list===")

    if not service_id or not isinstance(service_id, str):
        logger.warning("Invalid service_id provided: %s", service_id)
        return []

    url = f"{BASE_URL}/appointments/yclients/product"  # Убраны пробелы!

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
        product_name = servise_name.split(',')[0]
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
        return sequences_list, 'one'

    # Комплекс
    resp_json_modify  = update_services_in_sequences(resp_json)
    available_sequences = resp_json_modify.get("result", {}).get("available_sequences")
    if available_sequences and isinstance(available_sequences, list):
        # Список для выбора времени.
        sequences_list = [
            {'sequence_id': seq['sequence_id'], 'start_time': seq['total_start_time']}
            for seq in available_sequences
        ]
        # Список комплекса по которому нужно записать отдельно услуги.
        available_sequences_short_list = avaliable_sequences_short(available_sequences)
        return sequences_list, available_sequences_short_list

    return [], []


def update_services_in_sequences(data):
    replacements = {
        '2950601': {'master_id': '881127', 'master_name': 'Термотерапия'},
        '2950597': {'master_id': '864147', 'master_name': 'Прессотерапия'},
        '2950609': {'master_id': '914499', 'master_name': 'Ролик'},
        '2950603': {'master_id': '914503', 'master_name': 'Токовые Процедуры'}
    }
    # Оригинальная структура с доступом к available_sequences
    for seq in data['result']['available_sequences']:
        for step in seq['steps']:
            rid = step['service_id']
            if rid in replacements:
                step['master_id'] = replacements[rid]['master_id']
                step['master_name'] = replacements[rid]['master_name']
    return data

def avaliable_sequences_short(available_sequences):
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
        for seq in available_sequences
    ]
    return result

def filter_sequences_list(name: str, sequences_list: list[dict]):
    map_name = {
        "Прессотерапия": "Прессотерапия",
        "Роликовый массажер": "Ролик",
        "Термотерапия": "Термотерапия",
        "Электролиполиз": "Токовые Процедуры",
        "Электромиостимуляция": "Токовые Процедуры",
    }
    filter = [item for item in sequences_list if item['master_name']==map_name.get(name)]
    return filter


# Пример использования
if __name__ == "__main__":
    """Тестовый пример работы функции."""

    async def main():
        """Тестовый пример работы функции."""
        date = "2025-11-29"
        # service_id = "1-19501163"
        service_id = "7-2950601"
        # service_id = "7-2950601, 7-2950603"
        logger.info("Доступные мастера:")
        result = await avaliable_time_for_master_list_async(date=date, service_id=service_id)
        logger.info(result)

    asyncio.run(main())

# cd /home/copilot_superuser/petrunin/zena
# uv run python -m mcpserver.src.crm.avaliable_time_for_master