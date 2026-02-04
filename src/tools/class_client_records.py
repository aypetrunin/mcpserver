"""
class_client_records.py

MCP-инструмент (FastMCP tool) для получения текущих записей клиента.

КОНФИГУРАЦИЯ
-----------
Список каналов (channel_ids) передаётся из переменных окружения, например:

    CHANNEL_IDS_SOFIA=1,19

И читается при старте приложения:

    channel_ids = get_env_csv("CHANNEL_IDS_SOFIA")
    m = await MCPClientRecords.create(channel_ids=channel_ids)
    tool_records_sofia = m.get_tool()

ВАЖНО: ВСЕГДА ИЩЕМ ПО СПИСКУ channel_ids
---------------------------------------
Этот tool НЕ принимает channel_id как аргумент и НЕ умеет “single-channel” режим.

Логика:
- всегда выполняем поиск во всех каналах из self.channel_ids
- результаты агрегируем в один список
- если хотя бы один канал вернул success=True -> общий success=True
"""

from __future__ import annotations

import logging
import textwrap
from typing import Any, Dict

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from ..crm.crm_get_client_records import get_client_records  # type: ignore

logger = logging.getLogger(__name__)

class MCPClientRecords:
    """
    MCPClientRecords — MCP-обёртка над get_client_records.

    channel_ids:
    - передаются ОДИН РАЗ при создании инструмента (обычно из env: CHANNEL_IDS_*)
    - используются ВСЕГДА: мы всегда ищем записи по всем этим каналам и объединяем результат
    """

    def __init__(self, channel_ids: list[str]) -> None:
        # Список каналов (строками), например ["1", "19"]
        self.channel_ids: list[str] = channel_ids

        # Описание (инструкция) для LLM/агента
        self.description: str = self._set_description()

        # Создаём MCP-инструмент
        self.tool_records: FastMCP = FastMCP(name="records")

        # Регистрируем tool-функцию
        self._register_tool()

    @classmethod
    async def create(cls, channel_ids: list[str]) -> "MCPClientRecords":
        """
        Асинхронная фабрика (единый стиль как у других MCP-классов).

        channel_ids обычно получаем так:
            channel_ids = get_env_csv("CHANNEL_IDS_SOFIA")  # -> ["1", "19"]
        """
        if not channel_ids:
            raise RuntimeError(
                "channel_ids пустой. Проверь переменную окружения CHANNEL_IDS_*"
            )
        return cls(channel_ids=channel_ids)

    def _set_description(self) -> str:
        """
        Description — документация tool-а для LLM.
        Делаем её максимально точной: channel_id НЕ передаём, всегда ищем по self.channel_ids.
        """
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
        """
        Регистрируем MCP tool-функцию records.
        Она принимает только user_companychat и агрегирует по всем self.channel_ids.
        """

        @self.tool_records.tool(
            name="records",
            description=self.description,
        )
        async def records(user_companychat: str) -> Dict[str, Any]:
            # --- user_companychat: str -> int ---
            try:
                user_id_int = int(user_companychat)
            except ValueError:
                return {
                    "success": False,
                    "data": [],
                    "error": "Некорректный идентификатор пользователя",
                }

            logger.info(
                "[records] multi-channel only | "
                f"user={user_companychat}, channel_ids={self.channel_ids}"
            )

            # Сюда собираем все записи из всех каналов
            aggregated_data: list[Any] = []

            # Если все каналы “упали” — вернём success=False и ошибку
            last_error: str | None = None

            # Если хотя бы один канал успешен — success=True
            any_success = False

            # Проходим по всем каналам из env
            for ch in self.channel_ids:
                # channel_id в env хранится строкой -> приводим к int
                try:
                    ch_int = int(ch)
                except ValueError:
                    last_error = f"Некорректный channel_id в env: {ch}"
                    continue

                # Вызываем бизнес-функцию и ловим неожиданные исключения,
                # чтобы один “упавший” канал не ломал весь результат
                try:
                    resp = await get_client_records(
                        user_companychat=user_id_int,
                        channel_id=ch_int,
                    )
                except Exception as e:
                    last_error = str(e)
                    continue
                
                logger.info(f"resp: {resp}")
                # Ожидаем формат:
                # {"success": bool, "data": [...], "error": ...}
                if resp.get("success"):
                    any_success = True

                    data_part = resp.get("data") or []
                    # data ожидается как list, но на всякий случай страхуемся
                    if isinstance(data_part, list):
                        aggregated_data.extend(data_part)
                    else:
                        aggregated_data.append(data_part)
                else:
                    err = resp.get("error")
                    if isinstance(err, str) and err:
                        last_error = err

            # Финальный ответ
            return {
                "success": any_success,
                "data": aggregated_data,
                "error": None if any_success else (last_error or "Не удалось получить записи"),
            }

        return records

    def get_tool(self) -> FastMCP:
        """Возвращает FastMCP-инструмент для монтирования."""
        return self.tool_records

    def get_description(self) -> str:
        """Возвращает description (удобно для отладки)."""
        return self.description
