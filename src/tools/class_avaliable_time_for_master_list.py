# class_avaliable_time_for_master_list.py

"""MCP-инструмент для поиска свободных слотов по мастерам.

Используется для подбора доступного времени для одной услуги
или комплекса услуг с учётом тайм-зоны MCP-сервера.

КОНФИГУРАЦИЯ
------------
Тайм-зона задаётся на уровне MCP-сервера (агента) через env:

    MCP_TZ_SOFIA=Asia/Krasnoyarsk

ПРИМЕЧАНИЕ ПО ТАЙМ-ЗОНАМ
-----------------------
CRM-слой выполняет:
- сравнения "прошло/не прошло"
- сортировку слотов

Для этого в CRM-функцию обязательно передаётся server_name,
чтобы выбрать TZ из env MCP_TZ_<SERVER>.
"""

from __future__ import annotations

import asyncio
import logging
import textwrap
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from src.crm._crm_result import Payload, err, ok

from ..crm.crm_avaliable_time_for_master_list import (
    avaliable_time_for_master_list_async,  # type: ignore
)


logger = logging.getLogger(__name__)


class MCPAvailableTimeForMasterList:
    """MCP-обёртка над avaliable_time_for_master_list_async.

    server_name:
    - логическое имя сервера/агента (например: "sofia", "alisa")
    - нужно для корректной работы тайм-зон в CRM-слое (env MCP_TZ_<SERVER>)
    """

    def __init__(self, server_name: str) -> None:
        """
        Инициализировать MCP-инструмент поиска свободных слотов по мастерам.

        :param server_name: Логическое имя MCP-сервера/агента,
            используемое для выбора тайм-зоны в CRM-слое
            (env MCP_TZ_<SERVER>).
        """
        self.server_name: str = server_name
        self.description: str = self._set_description()

        self.tool_avaliable_time_for_master_list: FastMCP = FastMCP(
            name="avaliable_time_for_master_list"
        )
        self._register_tool()

    @classmethod
    async def create(cls, server_name: str) -> MCPAvailableTimeForMasterList:
        """
        Фабричный метод создания MCP-инструмента.

        Используется при инициализации MCP-сервера и выполняет
        fail-fast валидацию конфигурации.

        :param server_name: Логическое имя сервера/агента
            (например: "sofia", "alisa").
        :raises RuntimeError: Если server_name пустой или некорректный.
        :return: Инициализированный экземпляр MCPAvailableTimeForMasterList.
        """
        # Что делаем: fail-fast в create() — это конфиг, а не runtime input пользователя.
        # Если server_name пустой, лучше упасть при старте сервера.
        if not server_name or not isinstance(server_name, str):
            raise RuntimeError(
                "server_name пустой. Ожидается имя сервера/агента (например: 'sofia')."
            )
        return cls(server_name=server_name)

    def _set_description(self) -> str:
        # Что делаем: обновляем Returns под единый контракт ok/err.
        # Важно: data на успехе — tuple[list[dict], list[dict]] (как и раньше).
        return textwrap.dedent(
            """
            MCP tool: avaliable_time_for_master_list — поиск свободных слотов по мастерам (список услуг)

            Получение списка доступного времени для записи на выбранную услугу в указанный день.

            **Назначение:**
            Используется для определения, на какое время клиент может записаться на услугу в выбранную дату.
            Используется при онлайн-бронировании.

            **Примеры запросов:**
            - "Какие есть свободные слоты на УЗИ 5 августа?"
            - "Могу ли я записаться на приём к косметологу 12 июля?"
            - "Проверьте доступное время для гастроскопии на следующей неделе"
            - "Когда можно записаться к Кристине"
            - "Какие мастера могут выполнить услугу завтра"
            - "На ближайшее время?"

            **Args:**
            - `date` (`str`, required):
              Дата в формате YYYY-MM-DD. Пример: "2025-07-22"
            - `product_id` (`list[str]`, required):
              Список идентификаторов услуг. Пример: ["1-232324", "1-237654"]
            - `product_name` (`list[str]`, required):
              Список названий услуг.

            **Returns (единый контракт):**
            - ok(tuple[list[dict], list[dict]]):
                - Для одиночной услуги: (список мастеров со слотами, [])
                - Для комплекса: (список последовательностей, short_list последовательностей)
            - err(code, error) при ошибке
            """
        ).strip()

    def _register_tool(self) -> FunctionTool:
        @self.tool_avaliable_time_for_master_list.tool(
            name="avaliable_time_for_master_list",
            description=self.description,
        )
        async def avaliable_time_for_master_list(
            date: str,
            product_id: list[str],
            product_name: list[str],
        ) -> Payload[tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
            """Поиск свободных слотов по мастерам для списка услуг (единый контракт)."""
            # Что делаем: лёгкая валидация user input (tool args) -> err(validation_error).
            if not date or not isinstance(date, str) or not date.strip():
                return err(
                    code="validation_error", error="date обязателен (YYYY-MM-DD)"
                )

            if not isinstance(product_id, list) or not product_id:
                return err(
                    code="validation_error",
                    error="product_id должен быть непустым списком",
                )

            if not isinstance(product_name, list) or not product_name:
                return err(
                    code="validation_error",
                    error="product_name должен быть непустым списком",
                )

            # Что делаем: приводим к строкам и отфильтровываем пустые значения,
            # чтобы не отправлять мусор в CRM слой.
            clean_product_id = [str(x).strip() for x in product_id if str(x).strip()]
            clean_product_name = [
                str(x).strip() for x in product_name if str(x).strip()
            ]

            if not clean_product_id:
                return err(
                    code="validation_error",
                    error="product_id не содержит валидных значений",
                )

            if not clean_product_name:
                return err(
                    code="validation_error",
                    error="product_name не содержит валидных значений",
                )

            list_products_id = ", ".join(clean_product_id)
            list_products_name = ", ".join(clean_product_name)

            payload = {
                "date": date.strip(),
                "service_id": list_products_id,
                "service_name": list_products_name,
                "server_name": self.server_name,
            }

            logger.info(
                "[avaliable_time_for_master_list] вход | server=%s date=%s service_id=%s service_name=%s",
                self.server_name,
                payload["date"],
                payload["service_id"],
                payload["service_name"],
            )

            try:
                (
                    sequences,
                    avaliable_sequences,
                ) = await avaliable_time_for_master_list_async(**payload)
            except asyncio.CancelledError:
                # Что делаем: CancelledError не превращаем в err — важно для корректного shutdown supervisor'а.
                raise
            except Exception as exc:
                # Что делаем: любые неожиданные ошибки CRM-слоя -> единый err.
                # Детали оставляем в логах (по контракту err только code+error).
                logger.exception(
                    "[avaliable_time_for_master_list] failed | server=%s payload=%s error=%s",
                    self.server_name,
                    payload,
                    exc,
                )
                return err(
                    code="internal_error", error="Ошибка получения доступного времени"
                )

            logger.info(
                "[avaliable_time_for_master_list] выход | server=%s sequences_len=%s avaliable_sequences_len=%s",
                self.server_name,
                len(sequences) if isinstance(sequences, list) else -1,
                len(avaliable_sequences)
                if isinstance(avaliable_sequences, list)
                else -1,
            )

            # Что делаем: возвращаем строго ok(data) с тем же типом, что был раньше (tuple[list, list]).
            return ok((sequences, avaliable_sequences))

        return avaliable_time_for_master_list

    def get_tool(self) -> FastMCP:
        """Возвращает FastMCP-инструмент для монтирования."""
        return self.tool_avaliable_time_for_master_list

    def get_description(self) -> str:
        """Возвращает description (удобно для отладки)."""
        return self.description
