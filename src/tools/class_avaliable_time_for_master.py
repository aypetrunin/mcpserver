"""
class_avaliable_time_for_master.py

MCP-инструмент (FastMCP tool) для поиска свободных слотов по мастерам.

КОНФИГУРАЦИЯ
-----------
Список филиалов (office_ids/channel_ids) берётся из переменных окружения, например:

    CHANNEL_IDS_SOFIA=1,19

Также задаётся тайм-зона агента/сервера (IANA TZ), например:

    MCP_TZ_SOFIA=Asia/Krasnoyarsk

Использование:

    channel_ids = get_env_csv("CHANNEL_IDS_SOFIA")
    m = await MCPAvailableTimeForMaster.create(server_name="sofia", channel_ids=channel_ids)
    tool_avaliable_time_for_master = m.get_tool()

ЛОГИКА
------
- tool принимает office_id как аргумент (приоритетный филиал)
- сначала ищем в указанном office_id
- если слотов нет — параллельно ищем в остальных филиалах из self.channel_ids
- для каждого филиала при необходимости подбираем secondary product_id через Postgres

ПРИМЕЧАНИЕ ПО ТАЙМ-ЗОНАМ
------------------------
Сравнения "прошло/не прошло" и парсинг слотов выполняются внутри CRM-функции
avaliable_time_for_master_async(...). Для этого сюда прокидывается server_name,
чтобы CRM-слой мог корректно выбрать TZ из env MCP_TZ_<SERVER>.

Тайм-зона задаётся на уровне MCP-сервера (агента).
Все филиалы, обслуживаемые данным сервером, находятся в одной тайм-зоне,
поэтому office_id не участвует в выборе TZ.
"""

from __future__ import annotations

import asyncio
import logging
import textwrap
from typing import Any, Optional

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from ..crm.crm_avaliable_time_for_master import avaliable_time_for_master_async  # type: ignore
from ..postgres.postgres_util import read_secondary_article_by_primary  # type: ignore

logger = logging.getLogger(__name__)


class MCPAvailableTimeForMaster:
    """
    MCPAvailableTimeForMaster — MCP-обёртка над avaliable_time_for_master_async.

    server_name:
    - логическое имя сервера/агента (например: "sofia", "alisa")
    - нужно для корректной работы тайм-зон в CRM-слое (env MCP_TZ_<SERVER>)

    channel_ids:
    - передаются один раз при создании класса (обычно из env CHANNEL_IDS_*)
    - используются для fallback-поиска по другим филиалам
    """

    def __init__(self, server_name: str, channel_ids: list[str]) -> None:
        self.server_name: str = server_name
        self.channel_ids: list[str] = channel_ids

        self.description: str = self._set_description()

        self.tool_avaliable_time_for_master: FastMCP = FastMCP(
            name="avaliable_time_for_master"
        )

        self._register_tool()

    @classmethod
    async def create(
        cls,
        server_name: str,
        channel_ids: list[str],
    ) -> "MCPAvailableTimeForMaster":
        if not server_name:
            raise RuntimeError("server_name пустой. Ожидается имя сервера/агента (например: 'sofia').")
        if not channel_ids:
            raise RuntimeError(
                "channel_ids пустой. Проверь переменную окружения CHANNEL_IDS_*"
            )
        return cls(server_name=server_name, channel_ids=channel_ids)

    def _set_description(self) -> str:
        return textwrap.dedent(
            """
            MCP tool: avaliable_time_for_master — поиск свободных слотов по мастерам

            Возвращает список доступного времени для записи на услугу в выбранную дату.

            **Когда использовать:**
            - Клиент спрашивает свободные слоты на конкретную услугу
            - Нужно показать расписание мастеров по услуге

            **Примеры вопросов:**
            - Какие есть свободные слоты на УЗИ 5 августа?
            - Могу ли я записаться на приём к косметологу 12 июля?
            - Проверьте доступное время для гастроскопии на следующей неделе
            - Когда можно записаться к Кристине?

            **Args:**
            - `session_id` (`str`, required):
              id dialog session
            - `office_id` (`str`, required):
              id филиала (приоритетный филиал)
            - `product_id` (`str`, required):
              идентификатор услуги в формате "1-232324"
            - `date` (`str`, required):
              дата в формате YYYY-MM-DD

            **Returns:**
            list[dict]:
              [
                {
                  "office_id": "1",
                  "avaliable_time": [
                      {"master_name": "...", "master_id": 123, "master_slots": [...]}
                  ],
                  "message": "..."
                }
              ]
            """
        ).strip()

    def _register_tool(self) -> FunctionTool:
        @self.tool_avaliable_time_for_master.tool(
            name="avaliable_time_for_master",
            description=self.description,
        )
        async def avaliable_time_for_master(
            session_id: str,
            office_id: str,
            date: str,
            product_id: str,
        ) -> list[dict[str, Any]]:
            logger.info(
                "[avaliable_time_for_master] вход | "
                "server=%s session_id=%s office_id=%s date=%s product_id=%s channel_ids=%s",
                self.server_name,
                session_id,
                office_id,
                date,
                product_id,
                self.channel_ids,
            )

            response_list: list[dict[str, Any]] = []

            primary_product_id = product_id
            primary_channel = await self._extract_primary_channel(primary_product_id)

            # 1) пробуем указанный филиал
            product_for_office = await self._resolve_product_for_office(
                primary_product_id=primary_product_id,
                primary_channel=primary_channel,
                office_id=office_id,
            )

            response = await self._fetch_slots_for_office(
                date=date,
                product_id_for_office=product_for_office,
            )

            response_list.append(
                {
                    "office_id": office_id,
                    "avaliable_time": response,
                    "message": (
                        f"Есть доступное время для записи в филиале: {office_id}"
                        if response
                        else f"Нет доступного время для записи в филиале: {office_id}"
                    ),
                }
            )

            # 2) если пусто — пробуем другие филиалы (параллельно) из self.channel_ids
            if not response:
                other_offices = await self._filter_channel_ids(exclude=office_id)

                tasks: list[asyncio.Task[list[dict[str, Any]]]] = []
                office_order: list[str] = []

                for other_office_id in other_offices:
                    product_for_other = await self._resolve_product_for_office(
                        primary_product_id=primary_product_id,
                        primary_channel=primary_channel,
                        office_id=other_office_id,
                    )
                    tasks.append(
                        asyncio.create_task(
                            self._fetch_slots_for_office(
                                date=date,
                                product_id_for_office=product_for_other,
                            )
                        )
                    )
                    office_order.append(other_office_id)

                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for oid, res in zip(office_order, results):
                        if isinstance(res, Exception):
                            logger.warning(
                                "[avaliable_time_for_master] slots fetch failed "
                                "server=%s office_id=%s err=%s",
                                self.server_name,
                                oid,
                                res,
                            )
                            response_list.append(
                                {
                                    "office_id": oid,
                                    "avaliable_time": [],
                                    "message": f"Нет доступного время для записи в филиале: {oid}",
                                }
                            )
                            continue

                        response_list.append(
                            {
                                "office_id": oid,
                                "avaliable_time": res,
                                "message": (
                                    f"Есть доступное время для записи в филиале {oid}"
                                    if res
                                    else f"Нет доступного время для записи в филиале: {oid}"
                                ),
                            }
                        )

            logger.info(
                "[avaliable_time_for_master] выход | server=%s response_list=%s",
                self.server_name,
                response_list,
            )

            return response_list

        return avaliable_time_for_master

    async def _filter_channel_ids(self, exclude: Optional[str] = None) -> list[str]:
        ids = self.channel_ids

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

    async def _extract_primary_channel(self, product_id: str) -> str:
        parts = product_id.split("-", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Invalid product_id format: {product_id!r}. Expected like '1-232324'."
            )
        return parts[0]

    async def _resolve_product_for_office(
        self,
        primary_product_id: str,
        primary_channel: str,
        office_id: str,
    ) -> str:
        """Возвращает артикул услуги для конкретного филиала."""
        if office_id == primary_channel:
            return primary_product_id

        logger.info(
            "[avaliable_time_for_master] resolve product | "
            "server=%s primary_product_id=%s primary_channel=%s office_id=%s",
            self.server_name,
            primary_product_id,
            primary_channel,
            office_id,
        )

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
            "[avaliable_time_for_master] resolved | server=%s office_id=%s product_for_office=%s",
            self.server_name,
            office_id,
            product_for_office,
        )

        return product_for_office

    async def _fetch_slots_for_office(
        self,
        date: str,
        product_id_for_office: str,
    ) -> list[dict[str, Any]]:
        # server_name прокидываем в CRM-слой, чтобы тот мог корректно сравнивать слоты
        # относительно локального времени агента (env MCP_TZ_<SERVER>).
        return await avaliable_time_for_master_async(
            date,
            product_id_for_office,
            server_name=self.server_name,
        )

    def get_tool(self) -> FastMCP:
        """Возвращает FastMCP-инструмент для монтирования."""
        return self.tool_avaliable_time_for_master

    def get_description(self) -> str:
        """Возвращает description (удобно для отладки)."""
        return self.description
