"""MCP-сервер для поиска свободных слотов по мастерам."""

import os
import asyncio
import logging
from typing import Any, Optional

from fastmcp import FastMCP

from ..crm.crm_avaliable_time_for_master import avaliable_time_for_master_async  # type: ignore
from ..postgres.postgres_util import read_secondary_article_by_primary  # type: ignore


logger = logging.getLogger(__name__)

tool_avaliable_time_for_master = FastMCP(name="avaliable_time_for_master")

@tool_avaliable_time_for_master.tool(
    name="avaliable_time_for_master",
    description=(  # оставил как у вас
        "Получение списка доступного времени для записи на выбранную услугу в указанный день.\n\n"
        "**Назначение:**\n"
        "Используется для определения, на какое время клиент может записаться на услугу в выбранную дату.  "
        "Используется при онлайн-бронировании.\n\n"
        "**Примеры запросов:**\n"
        '- "Какие есть свободные слоты на УЗИ 5 августа?"\n'
        '- "Могу ли я записаться на приём к косметологу 12 июля?"\n'
        '- "Проверьте доступное время для гастроскопии на следующей неделе"\n\n'
        '- "Когда можно записаться к Кристине"\n\n'
        '- "Какие мастера могут выполнить услугу завтра."\n\n'
        "**Args:**\n"
        "- session_id(str): id dialog session. **Обязательный параметр.**\n"
        "- office_id(str): id филиала. **Обязательный параметр.**\n"
        "- product_id (str): Идентификатор медицинской услуги. Обязательно две цифры разделенные дефисом. Пример формата: '1-232324'. **Обязательный параметр.**\n\n"
        "- date (str): Дата на которую хочет записатьсяклиент в формате DD.MM.YYYY-MM-DD . Пример: '2025-07-22' **Обязательный параметр.**\n"
        "**Returns:**\n"
        "list[dict]: Список доступных слотов на услугу в формате DD.MM.YYYY-MM-DD  по мастерам [{'master_name': 'Кузнецова Кристина Александровна', 'master_id': 4216657, 'master_slots': ['2025-09-26 9:00', '2025-09-26 10:00', '2025-09-26 10:30']}]"
    ),
)
async def available_time_for_master(
    session_id: str,
    office_id: str,
    date: str,
    product_id: str,
) -> list[dict[str, Any]]:
    """Функция поиска свободных слотов."""
    logger.info(
        "mcp_available_time_for_master office_id=%s date=%s product_id=%s",
        office_id, date, product_id,
    )

    response_list: list[dict[str, Any]] = []

    primary_product_id = product_id
    primary_channel = await _extract_primary_channel(primary_product_id)

    # 1) пробуем указанный филиал
    product_for_office = await _resolve_product_for_office(
        primary_product_id=primary_product_id,
        primary_channel=primary_channel,
        office_id=office_id,
    )

    response = await _fetch_slots_for_office(date, product_for_office)

    response_list.append({
        "office_id": office_id,
        "available_time": response,
        "message": f"Есть доступное время для записи в филиале: {office_id}" if response else f"Нет доступного время для записи в филиале: {office_id}"
    })

    # 2) если пусто — пробуем другие филиалы (параллельно)
    if not response:
        other_offices = await _parse_channel_ids("CHANNEL_IDS_SOFIA", exclude=office_id)

        tasks: list[asyncio.Task[list[dict[str, Any]]]] = []
        office_order: list[str] = []

        for other_office_id in other_offices:
            product_for_other = await _resolve_product_for_office(
                primary_product_id=primary_product_id,
                primary_channel=primary_channel,
                office_id=other_office_id,
            )
            tasks.append(asyncio.create_task(_fetch_slots_for_office(date, product_for_other)))
            office_order.append(other_office_id)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for oid, res in zip(office_order, results):
                if isinstance(res, Exception):
                    logger.warning("slots fetch failed for office_id=%s: %s", oid, res)
                    response_list.append({
                        "office_id": oid,
                        "available_time": [],
                        "message": f"Нет доступного время для записи в филиале: {oid}",
                    })
                    continue

                response_list.append({
                    "office_id": oid,
                    "available_time": res,
                    "message": f"Есть доступное время для записи в филиале {oid}" if res else f"Нет доступного время для записи в филиале: {oid}",
                })

    return response_list


async def _parse_channel_ids(env_name: str, exclude: Optional[str] = None) -> list[str]:
    raw = os.getenv(env_name, "")  # безопасно, даже если переменная не задана
    ids = [x.strip() for x in raw.split(",") if x.strip()]
    if exclude is not None:
        ids = [x for x in ids if x != exclude]
    # сохраняем порядок, но убираем дубли
    seen: set[str] = set()
    uniq: list[str] = []
    for x in ids:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


async def _extract_primary_channel(product_id: str) -> str:
    # ожидаем формат "1-232324"
    parts = product_id.split("-", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Invalid product_id format: {product_id!r}. Expected like '1-232324'."
        )
    return parts[0]


async def _resolve_product_for_office(
    primary_product_id: str,
    primary_channel: str,
    office_id: str,
) -> str:
    """Возвращает артикул услуги для конкретного филиала."""
    if office_id == primary_channel:
        return primary_product_id

    logger.info("===_resolve_product_for_office===")

    # ✅ ВАЖНО: Postgres/asyncpg хочет int, поэтому приводим
    try:
        primary_channel_int = int(primary_channel)
        office_id_int = int(office_id)
    except ValueError:
        raise ValueError(
            f"Invalid channel/office id. primary_channel={primary_channel!r}, office_id={office_id!r}"
        )

    product_for_office = await read_secondary_article_by_primary(
        primary_article=primary_product_id,
        primary_channel=primary_channel_int,
        secondary_channel=office_id_int,
    )

    logger.info(
        "primary_product_id=%s office_id=%s product_for_office=%s",
        primary_product_id, office_id, product_for_office
    )
    return product_for_office



async def _fetch_slots_for_office(date: str, product_id_for_office: str) -> list[dict[str, Any]]:
    return await avaliable_time_for_master_async(date, product_id_for_office)
