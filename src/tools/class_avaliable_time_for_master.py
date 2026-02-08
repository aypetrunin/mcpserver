"""MCP-инструмент (FastMCP tool) для поиска свободных слотов по мастерам.

КОНФИГУРАЦИЯ
-----------
Список филиалов (office_ids/channel_ids) берётся из переменных окружения, например:

    CHANNEL_IDS_SOFIA=1,19

Также задаётся тайм-зона агента/сервера (IANA TZ), например:

    MCP_TZ_SOFIA=Asia/Krasnoyarsk

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
import time
from typing import Any
import uuid

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from src.crm._crm_result import Payload, err, ok

from ..crm.crm_avaliable_time_for_master import (
    avaliable_time_for_master_async,  # type: ignore
)
from ..postgres.postgres_util import read_secondary_article_by_primary  # type: ignore


logger = logging.getLogger(__name__)


class MCPAvailableTimeForMaster:
    """MCPAvailableTimeForMaster — MCP-обёртка над avaliable_time_for_master_async."""

    def __init__(self, server_name: str, channel_ids: list[str]) -> None:
        """
        Инициализировать MCP-инструмент поиска свободных слотов по мастерам.

        :param server_name: Логическое имя MCP-сервера/агента, используемое
            CRM-слоем для выбора тайм-зоны (env MCP_TZ_<SERVER>).
        :param channel_ids: Список филиалов/каналов (office_ids/channel_ids),
            которые обслуживает данный MCP-сервер.
        """
        self.server_name: str = server_name
        self.channel_ids: list[str] = channel_ids

        self.description: str = self._set_description()
        self.tool_avaliable_time_for_master: FastMCP = FastMCP(
            name="avaliable_time_for_master"
        )
        self._register_tool()

    @classmethod
    async def create(
        cls, server_name: str, channel_ids: list[str]
    ) -> MCPAvailableTimeForMaster:
        """
        Фабричный метод создания MCP-инструмента.

        Используется при старте MCP-сервера и выполняет fail-fast проверку
        конфигурации (server_name и channel_ids).

        :param server_name: Логическое имя сервера/агента (например: "sofia").
        :param channel_ids: Список channel_ids/office_ids из конфигурации (env).
        :raises RuntimeError: Если server_name пустой или channel_ids пустой.
        :return: Инициализированный экземпляр MCPAvailableTimeForMaster.
        """
        # Что делаем: fail-fast на конфиге (server_name/channel_ids) при старте сервера.
        if not server_name:
            raise RuntimeError(
                "server_name пустой. Ожидается имя сервера/агента (например: 'sofia')."
            )
        if not channel_ids:
            raise RuntimeError(
                "channel_ids пустой. Проверь переменную окружения CHANNEL_IDS_*"
            )
        return cls(server_name=server_name, channel_ids=channel_ids)

    def _set_description(self) -> str:
        # Что делаем: обновляем Returns под единый контракт ok/err.
        # На успехе возвращаем list[dict] (как и раньше), но внутри ok(...).
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
            - `session_id` (`str`, required): id dialog session
            - `office_id` (`str`, required): id филиала (приоритетный филиал)
            - `product_id` (`str`, required): идентификатор услуги в формате "1-232324"
            - `date` (`str`, required): дата в формате YYYY-MM-DD

            **Returns (единый контракт):**
            - ok(list[dict]) — список филиалов с доступным временем (может быть пустым/частично пустым)
            - err(code,error) — ошибка валидации/конфига/внутренняя ошибка
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
        ) -> Payload[list[dict[str, Any]]]:
            # trace id для склейки логов одного запроса
            trace_id = uuid.uuid4().hex[:10]
            t0 = time.perf_counter()

            def ms(since: float) -> int:
                return int((time.perf_counter() - since) * 1000)

            logger.info(
                "[avaliable_time_for_master][%s] START | server=%s session_id=%r office_id=%r date=%r product_id=%r channel_ids=%s",
                trace_id,
                self.server_name,
                session_id,
                office_id,
                date,
                product_id,
                self.channel_ids,
            )

            # 0) Валидация входа
            t_val = time.perf_counter()
            if not session_id or not str(session_id).strip():
                logger.warning(
                    "[avaliable_time_for_master][%s] VALIDATION_FAIL | field=session_id duration_ms=%s",
                    trace_id,
                    ms(t_val),
                )
                return err(code="validation_error", error="session_id обязателен")

            if not office_id or not str(office_id).strip():
                logger.warning(
                    "[avaliable_time_for_master][%s] VALIDATION_FAIL | field=office_id duration_ms=%s",
                    trace_id,
                    ms(t_val),
                )
                return err(code="validation_error", error="office_id обязателен")

            if not date or not str(date).strip():
                logger.warning(
                    "[avaliable_time_for_master][%s] VALIDATION_FAIL | field=date duration_ms=%s",
                    trace_id,
                    ms(t_val),
                )
                return err(
                    code="validation_error", error="date обязателен (YYYY-MM-DD)"
                )

            if not product_id or not str(product_id).strip():
                logger.warning(
                    "[avaliable_time_for_master][%s] VALIDATION_FAIL | field=product_id duration_ms=%s",
                    trace_id,
                    ms(t_val),
                )
                return err(
                    code="validation_error",
                    error="product_id обязателен (например '1-232324')",
                )

            logger.info(
                "[avaliable_time_for_master][%s] VALIDATION_OK | duration_ms=%s",
                trace_id,
                ms(t_val),
            )

            # 1) primary_channel из product_id
            t_pc = time.perf_counter()
            try:
                primary_channel = await self._extract_primary_channel(product_id)
                logger.info(
                    "[avaliable_time_for_master][%s] PRIMARY_CHANNEL_OK | product_id=%r primary_channel=%r duration_ms=%s",
                    trace_id,
                    product_id,
                    primary_channel,
                    ms(t_pc),
                )
            except ValueError as exc:
                logger.warning(
                    "[avaliable_time_for_master][%s] PRIMARY_CHANNEL_FAIL | product_id=%r err=%s duration_ms=%s",
                    trace_id,
                    product_id,
                    exc,
                    ms(t_pc),
                )
                return err(
                    code="validation_error",
                    error="Некорректный формат product_id (ожидается 'X-YYYY')",
                )

            response_list: list[dict[str, Any]] = []

            # 2) Приоритетный офис: resolve продукта
            t_resolve_primary = time.perf_counter()
            try:
                logger.info(
                    "[avaliable_time_for_master][%s] RESOLVE_PRIMARY_START | office_id=%r primary_channel=%r primary_product_id=%r",
                    trace_id,
                    office_id,
                    primary_channel,
                    product_id,
                )
                product_for_office = await self._resolve_product_for_office(
                    primary_product_id=product_id,
                    primary_channel=primary_channel,
                    office_id=office_id,
                )
                logger.info(
                    "[avaliable_time_for_master][%s] RESOLVE_PRIMARY_OK | office_id=%r resolved_product=%r duration_ms=%s",
                    trace_id,
                    office_id,
                    product_for_office,
                    ms(t_resolve_primary),
                )
            except asyncio.CancelledError:
                logger.warning(
                    "[avaliable_time_for_master][%s] CANCELLED_DURING_RESOLVE_PRIMARY | duration_ms=%s",
                    trace_id,
                    ms(t_resolve_primary),
                )
                raise
            except ValueError as exc:
                logger.warning(
                    "[avaliable_time_for_master][%s] RESOLVE_PRIMARY_VALIDATION_FAIL | office_id=%r err=%s duration_ms=%s",
                    trace_id,
                    office_id,
                    exc,
                    ms(t_resolve_primary),
                )
                return err(
                    code="validation_error",
                    error="Некорректные идентификаторы office_id/channel_id",
                )
            except Exception as exc:
                logger.exception(
                    "[avaliable_time_for_master][%s] RESOLVE_PRIMARY_FAIL | office_id=%r err=%s duration_ms=%s",
                    trace_id,
                    office_id,
                    exc,
                    ms(t_resolve_primary),
                )
                return err(
                    code="internal_error", error="Ошибка получения доступного времени"
                )

            # 3) Приоритетный офис: fetch слотов
            t_fetch_primary = time.perf_counter()
            try:
                logger.info(
                    "[avaliable_time_for_master][%s] FETCH_PRIMARY_START | office_id=%r date=%r resolved_product=%r server_name=%r",
                    trace_id,
                    office_id,
                    date,
                    product_for_office,
                    self.server_name,
                )
                response = await self._fetch_slots_for_office(
                    date=date, product_id_for_office=product_for_office
                )
                logger.info(
                    "[avaliable_time_for_master][%s] FETCH_PRIMARY_OK | office_id=%r slots_count=%s duration_ms=%s",
                    trace_id,
                    office_id,
                    len(response),
                    ms(t_fetch_primary),
                )
                # при необходимости — очень подробный лог payload (осторожно с объемом)
                logger.debug(
                    "[avaliable_time_for_master][%s] FETCH_PRIMARY_PAYLOAD | office_id=%r slots=%s",
                    trace_id,
                    office_id,
                    response,
                )
            except asyncio.CancelledError:
                logger.warning(
                    "[avaliable_time_for_master][%s] CANCELLED_DURING_FETCH_PRIMARY | duration_ms=%s",
                    trace_id,
                    ms(t_fetch_primary),
                )
                raise
            except Exception as exc:
                logger.exception(
                    "[avaliable_time_for_master][%s] FETCH_PRIMARY_FAIL | office_id=%r err=%s duration_ms=%s",
                    trace_id,
                    office_id,
                    exc,
                    ms(t_fetch_primary),
                )
                return err(
                    code="internal_error", error="Ошибка получения доступного времени"
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

            # 4) Если пусто — параллельный поиск по остальным офисам
            if not response:
                t_other = time.perf_counter()
                other_offices = await self._filter_channel_ids(exclude=office_id)
                logger.info(
                    "[avaliable_time_for_master][%s] OTHER_OFFICES | exclude=%r other_offices=%s duration_ms=%s",
                    trace_id,
                    office_id,
                    other_offices,
                    ms(t_other),
                )

                # 4.1) resolve продуктов для других офисов
                t_resolve_others = time.perf_counter()
                offices_to_query: list[tuple[str, str]] = []
                for other_office_id in other_offices:
                    t_one = time.perf_counter()
                    try:
                        logger.info(
                            "[avaliable_time_for_master][%s] RESOLVE_OTHER_START | office_id=%r",
                            trace_id,
                            other_office_id,
                        )
                        product_for_other = await self._resolve_product_for_office(
                            primary_product_id=product_id,
                            primary_channel=primary_channel,
                            office_id=other_office_id,
                        )
                        offices_to_query.append((other_office_id, product_for_other))
                        logger.info(
                            "[avaliable_time_for_master][%s] RESOLVE_OTHER_OK | office_id=%r resolved_product=%r duration_ms=%s",
                            trace_id,
                            other_office_id,
                            product_for_other,
                            ms(t_one),
                        )
                    except Exception as exc:
                        logger.warning(
                            "[avaliable_time_for_master][%s] RESOLVE_OTHER_FAIL | office_id=%r err_type=%s err=%s duration_ms=%s",
                            trace_id,
                            other_office_id,
                            type(exc).__name__,
                            exc,
                            ms(t_one),
                        )
                        response_list.append(
                            {
                                "office_id": other_office_id,
                                "avaliable_time": [],
                                "message": f"Нет доступного время для записи в филиале: {other_office_id}",
                            }
                        )

                logger.info(
                    "[avaliable_time_for_master][%s] RESOLVE_OTHERS_DONE | to_query=%s duration_ms=%s",
                    trace_id,
                    offices_to_query,
                    ms(t_resolve_others),
                )

                # 4.2) параллельный fetch слотов
                t_fetch_others = time.perf_counter()
                tasks: list[asyncio.Task[list[dict[str, Any]]]] = []
                office_order: list[str] = []

                for oid, product_for_oid in offices_to_query:
                    logger.info(
                        "[avaliable_time_for_master][%s] FETCH_OTHER_SCHEDULE | office_id=%r date=%r resolved_product=%r",
                        trace_id,
                        oid,
                        date,
                        product_for_oid,
                    )
                    tasks.append(
                        asyncio.create_task(
                            self._fetch_slots_for_office(
                                date=date, product_id_for_office=product_for_oid
                            ),
                            name=f"fetch_slots:{trace_id}:{oid}",
                        )
                    )
                    office_order.append(oid)

                if tasks:
                    logger.info(
                        "[avaliable_time_for_master][%s] FETCH_OTHERS_START | offices=%s tasks=%s",
                        trace_id,
                        office_order,
                        len(tasks),
                    )
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    logger.info(
                        "[avaliable_time_for_master][%s] FETCH_OTHERS_DONE | duration_ms=%s",
                        trace_id,
                        ms(t_fetch_others),
                    )

                    for oid, res in zip(office_order, results):
                        if isinstance(res, Exception):
                            logger.warning(
                                "[avaliable_time_for_master][%s] FETCH_OTHER_FAIL | office_id=%r err_type=%s err=%s",
                                trace_id,
                                oid,
                                type(res).__name__,
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

                        logger.info(
                            "[avaliable_time_for_master][%s] FETCH_OTHER_OK | office_id=%r slots_count=%s",
                            trace_id,
                            oid,
                            len(res),
                        )
                        logger.debug(
                            "[avaliable_time_for_master][%s] FETCH_OTHER_PAYLOAD | office_id=%r slots=%s",
                            trace_id,
                            oid,
                            res,
                        )
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
                else:
                    logger.info(
                        "[avaliable_time_for_master][%s] FETCH_OTHERS_SKIPPED | reason=no_offices_to_query",
                        trace_id,
                    )

            logger.info(
                "[avaliable_time_for_master][%s] END | server=%s total_duration_ms=%s response_offices=%s",
                trace_id,
                self.server_name,
                ms(t0),
                [x.get("office_id") for x in response_list],
            )
            logger.debug(
                "[avaliable_time_for_master][%s] RESPONSE_PAYLOAD | %s",
                trace_id,
                response_list,
            )
            return ok(response_list)

        return avaliable_time_for_master

    async def _filter_channel_ids(self, exclude: str | None = None) -> list[str]:
        # Что делаем: сохраняем порядок и убираем дубли, опционально исключаем office.
        ids = self.channel_ids
        if exclude is not None:
            ids = [x for x in ids if x != exclude]

        seen: set[str] = set()
        uniq: list[str] = []
        for x in ids:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        return uniq

    async def _extract_primary_channel(self, product_id: str) -> str:
        """Выделяем channel_id из из переданного первоначального product_id."""
        # Что делаем: жёстко валидируем формат "X-YYYY".
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
        """Получить артикул услуги для конкретного филиала."""
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
        except ValueError as exc:
            raise ValueError(
                "Invalid channel/office id. "
                f"primary_channel={primary_channel!r}, office_id={office_id!r}"
            ) from exc

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
        self, date: str, product_id_for_office: str
    ) -> list[dict[str, Any]]:
        # Что делаем: пробрасываем server_name в CRM-слой для корректной TZ-логики.
        return await avaliable_time_for_master_async(
            date,
            product_id_for_office,
            server_name=self.server_name,
        )

    def get_tool(self) -> FastMCP:
        """Вернуть FastMCP-инструмент для монтирования."""
        return self.tool_avaliable_time_for_master

    def get_description(self) -> str:
        """Вернуть description (удобно для отладки)."""
        return self.description
