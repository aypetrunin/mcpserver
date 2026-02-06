"""MCP-инструмент для получения текущих записей клиента.

Инструмент выполняет поиск записей клиента во всех каналах из channel_ids,
агрегирует результаты и возвращает единый ответ.
"""

from __future__ import annotations

import logging
import textwrap
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from ..crm.crm_get_client_records import get_client_records  # type: ignore


logger = logging.getLogger(__name__)


class MCPClientRecords:
    """MCPClientRecords — MCP-обёртка над get_client_records.

    channel_ids:
    - передаются один раз при создании инструмента (обычно из env: CHANNEL_IDS_*)
    - используются всегда: поиск выполняется по всем каналам и результаты объединяются
    """

    def __init__(self, channel_ids: list[str]) -> None:
        """Инициализировать MCP-инструмент работы с записями клиента.

        Сохраняет список каналов, формирует описание инструмента для LLM
        и регистрирует MCP tool для работы с записями.
        """
        self.channel_ids: list[str] = channel_ids
        self.description: str = self._set_description()

        self.tool_records: FastMCP = FastMCP(name="records")
        self._register_tool()

    @classmethod
    async def create(cls, channel_ids: list[str]) -> MCPClientRecords:
        """Создать экземпляр MCPClientRecords.

        channel_ids обычно получаем так:
            channel_ids = get_env_csv("CHANNEL_IDS_SOFIA")  # -> ["1", "19"]
        """
        if not channel_ids:
            raise RuntimeError("channel_ids пустой. Проверь переменную окружения CHANNEL_IDS_*")
        return cls(channel_ids=channel_ids)

    def _set_description(self) -> str:
        """Сформировать документацию tool-а для LLM."""
        return textwrap.dedent(
            """
            MCP tool: records — текущие записи клиента

            Возвращает список услуг, на которые записан клиент.

            **Когда использовать:**
            - Клиент спрашивает, когда/куда/к кому он записан
            - Нужно показать расписание клиента, чтобы перенести/отменить визит

            **Примеры вопросов:**
            - Когда у меня запись?
            - На какое время я записан?
            - К кому и куда я записан?

            **ВАЖНОЕ ПРАВИЛО:**
            Инструмент ВСЕГДА ищет записи по всем каналам,
            которые были заранее заданы при создании MCP-инструмента
            (через переменные окружения `CHANNEL_IDS_*`).

            **Args:**
            - `user_companychat` (`str`, required):
              Идентификатор пользователя.

            **Returns:**
            dict:
              {
                "success": bool,
                "data": list,
                "error": str | None
              }
            """
        ).strip()

    def _register_tool(self) -> FunctionTool:
        """Зарегистрировать MCP tool-функцию records.

        Функция принимает только user_companychat и агрегирует результат
        по всем self.channel_ids.
        """

        @self.tool_records.tool(
            name="records",
            description=self.description,
        )
        async def records(user_companychat: str) -> dict[str, Any]:
            try:
                user_id_int = int(user_companychat)
            except ValueError:
                return {
                    "success": False,
                    "data": [],
                    "error": "Некорректный идентификатор пользователя",
                }

            logger.info(
                "[records] multi-channel only | user=%s, channel_ids=%s",
                user_companychat,
                self.channel_ids,
            )

            aggregated_data: list[Any] = []
            last_error: str | None = None
            any_success = False

            for ch in self.channel_ids:
                try:
                    ch_int = int(ch)
                except ValueError:
                    last_error = f"Некорректный channel_id в env: {ch}"
                    continue

                try:
                    resp = await get_client_records(
                        user_companychat=user_id_int,
                        channel_id=ch_int,
                    )
                except Exception as exc:
                    last_error = str(exc)
                    continue

                logger.info("[records] channel=%s resp=%s", ch, resp)

                if resp.get("success"):
                    any_success = True
                    data_part = resp.get("data") or []

                    if isinstance(data_part, list):
                        aggregated_data.extend(data_part)
                    else:
                        aggregated_data.append(data_part)
                else:
                    err = resp.get("error")
                    if isinstance(err, str) and err:
                        last_error = err

            return {
                "success": any_success,
                "data": aggregated_data,
                "error": None if any_success else (last_error or "Не удалось получить записи"),
            }

        return records

    def get_tool(self) -> FastMCP:
        """Вернуть FastMCP-инструмент для монтирования."""
        return self.tool_records

    def get_description(self) -> str:
        """Вернуть description (удобно для отладки)."""
        return self.description

