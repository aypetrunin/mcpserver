"""MCP-инструмент для получения текущих записей клиента.

Инструмент выполняет поиск записей клиента во всех каналах из channel_ids,
агрегирует результаты и возвращает единый ответ (ok/err).
"""

from __future__ import annotations

import logging
import textwrap
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from src.crm._crm_result import Payload, err, ok

from ..crm.crm_get_client_records import get_client_records  # type: ignore


logger = logging.getLogger(__name__)


class MCPClientRecords:
    """MCPClientRecords — MCP-обёртка над get_client_records.

    channel_ids:
    - передаются один раз при создании инструмента (обычно из env: CHANNEL_IDS_*)
    - используются всегда: поиск выполняется по всем каналам и результаты объединяются
    """

    def __init__(self, channel_ids: list[str]) -> None:
        """
        Инициализировать MCP-инструмент получения текущих записей клиента.

        :param channel_ids: Список идентификаторов каналов (строками),
            по которым выполняется поиск и агрегация записей.
        """
        self.channel_ids: list[str] = channel_ids
        self.description: str = self._set_description()

        self.tool_records: FastMCP = FastMCP(name="records")
        self._register_tool()

    @classmethod
    async def create(cls, channel_ids: list[str]) -> MCPClientRecords:
        """Создать экземпляр MCPClientRecords."""
        if not channel_ids:
            raise RuntimeError(
                "channel_ids пустой. Проверь переменную окружения CHANNEL_IDS_*"
            )
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
            - `user_companychat` (`str`, required): идентификатор пользователя (число строкой)

            **Returns (единый контракт):**
            - ok(list[...]) — CRM без ошибок (список может быть пустым)
            - err(code, error) — CRM/сеть/конфиг/валидация
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
        async def records(user_companychat: str) -> Payload[list[Any]]:
            # 1) Валидация аргумента
            try:
                user_id_int = int(user_companychat)
            except (TypeError, ValueError):
                return err(
                    code="validation_error",
                    error="Некорректный идентификатор пользователя: user_companychat должен быть числом.",
                )

            # 2) Валидация/нормализация channel_ids (конфиг)
            channel_ints: list[int] = []
            for ch in self.channel_ids:
                try:
                    channel_ints.append(int(ch))
                except (TypeError, ValueError):
                    logger.error("[records] invalid channel_id in env: %r", ch)
                    return err(
                        code="config_error",
                        error=f"Некорректный channel_id в конфигурации: {ch!r}",
                    )

            logger.info(
                "[records] multi-channel only | user=%s, channel_ids=%s",
                user_id_int,
                channel_ints,
            )

            # 3) Запросы по каналам + агрегация
            aggregated: list[Any] = []
            any_success = False
            last_err_code: str | None = None
            last_err_text: str | None = None

            for ch_int in channel_ints:
                resp = await get_client_records(
                    user_companychat=user_id_int,
                    channel_id=ch_int,
                )

                if resp["success"]:
                    any_success = True
                    data_part = resp["data"]
                    # data_part уже list по контракту get_client_records
                    aggregated.extend(data_part)
                else:
                    # если хоть один канал вернул err — запомним последнюю ошибку,
                    # но НЕ прерываемся: возможно, другой канал даст ok([])
                    last_err_code = resp.get("code") or last_err_code
                    last_err_text = resp.get("error") or last_err_text

            # 4) Итог
            # Правило: success=True означает "CRM без ошибок" — нам достаточно, чтобы
            # ХОТЯ БЫ ОДИН канал отработал ok (даже если вернул пусто).
            if any_success:
                return ok(aggregated)

            return err(
                code=last_err_code or "crm_unavailable",
                error=last_err_text or "Не удалось получить записи",
            )

        return records

    def get_tool(self) -> FastMCP:
        """Вернуть FastMCP-инструмент для монтирования."""
        return self.tool_records

    def get_description(self) -> str:
        """Вернуть description (удобно для отладки)."""
        return self.description
