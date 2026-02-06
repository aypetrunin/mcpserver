"""
class_avaliable_time_for_master_list.py

MCP-инструмент (FastMCP tool) для поиска свободных слотов по мастерам
для списка услуг (одиночная услуга или комплекс).

КОНФИГУРАЦИЯ
-----------
Тайм-зона задаётся на уровне MCP-сервера (агента) через env:

    MCP_TZ_SOFIA=Asia/Krasnoyarsk

Использование:

    m = await MCPAvailableTimeForMasterList.create(server_name="sofia")
    tool = m.get_tool()

ПРИМЕЧАНИЕ ПО ТАЙМ-ЗОНАМ
------------------------
CRM-слой выполняет:
- сравнения "прошло/не прошло"
- сортировку слотов

Для этого в CRM-функцию обязательно передаётся server_name,
чтобы выбрать TZ из env MCP_TZ_<SERVER>.
"""

from __future__ import annotations

import logging
import textwrap
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from ..crm.crm_avaliable_time_for_master_list import (
    avaliable_time_for_master_list_async,  # type: ignore
)

logger = logging.getLogger(__name__)


class MCPAvailableTimeForMasterList:
    """
    MCPAvailableTimeForMasterList — MCP-обёртка над avaliable_time_for_master_list_async.

    server_name:
    - логическое имя сервера/агента (например: "sofia", "alisa")
    - нужно для корректной работы тайм-зон в CRM-слое (env MCP_TZ_<SERVER>)
    """

    def __init__(self, server_name: str) -> None:
        self.server_name: str = server_name

        self.description: str = self._set_description()

        self.tool_avaliable_time_for_master_list: FastMCP = FastMCP(
            name="avaliable_time_for_master_list"
        )

        self._register_tool()

    @classmethod
    async def create(cls, server_name: str) -> "MCPAvailableTimeForMasterList":
        if not server_name or not isinstance(server_name, str):
            raise RuntimeError(
                "server_name пустой. Ожидается имя сервера/агента (например: 'sofia')."
            )
        return cls(server_name=server_name)

    def _set_description(self) -> str:
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

            **Returns:**
            tuple[list[dict], list[dict]]:
              - Для одиночной услуги: (список мастеров со слотами, [])
              - Для комплекса: (список последовательностей, short_list последовательностей)
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
        ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
            """
            Функция поиска свободных слотов по мастерам для списка услуг.
            """

            list_products_id = ", ".join(product_id)
            list_products_name = ", ".join(product_name)

            payload = {
                "date": date,
                "service_id": list_products_id,
                "service_name": list_products_name,
                "server_name": self.server_name,
            }

            logger.info(
                "[avaliable_time_for_master_list] вход | server=%s date=%s service_id=%s service_name=%s",
                self.server_name,
                date,
                list_products_id,
                list_products_name,
            )

            sequences, avaliable_sequences = await avaliable_time_for_master_list_async(
                **payload
            )

            logger.info(
                "[avaliable_time_for_master_list] выход | server=%s sequences=%s avaliable_sequences=%s",
                self.server_name,
                sequences,
                avaliable_sequences,
            )

            return sequences, avaliable_sequences

        return avaliable_time_for_master_list

    def get_tool(self) -> FastMCP:
        """Возвращает FastMCP-инструмент для монтирования."""
        return self.tool_avaliable_time_for_master_list

    def get_description(self) -> str:
        """Возвращает description (удобно для отладки)."""
        return self.description
