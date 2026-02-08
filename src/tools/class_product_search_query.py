"""Универсальный класс создания MCP-сервера поиска услуг (только по query).

Контракт ответа: только ok()/err() из _crm_result.py
- ok(list[dict]) — поиск выполнен, список может быть пустым
- err(code, error) — ошибка валидации/внутренняя ошибка
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from src.crm._crm_result import Payload, err, ok

from ..qdrant.retriever_product import retriever_product_hybrid_async  # type: ignore


logger = logging.getLogger(__name__)


class MCPSearchProductQuery:
    """Универсальный класс создания MCP-сервера поиска услуг (по query)."""

    def __init__(self, channel_ids: list[str]) -> None:
        """
        Инициализация MCP-сервера поиска услуг.

        :param channel_ids: Список идентификаторов каналов,
            по которым выполняется поиск услуг.
        """
        self.channel_ids: list[str] = channel_ids
        self.description: str = self._set_description()
        self.tool_product_search: FastMCP = FastMCP(name="product_search")
        self._register_tool()

    def get_description(self) -> str:
        """
        Получить описание MCP-инструмента.

        :return: Текстовое описание инструмента поиска услуг.
        """
        return self.description

    def _set_description(self) -> str:
        return """
Поиск услуг по текстовому запросу (query).

**Args:**
- `session_id` (str, required): ID dialog session.
- `query` (str, required): Свободный текст (название услуги/процедуры/категории).

**Returns (единый контракт):**
- ok(List[dict]) — список услуг (может быть пустым)
- err(code,error) — ошибка валидации/внутренняя ошибка

Каждая услуга:
- product_id (str): идентификатор услуги
- product_name (str): название услуги
- duration (int): длительность (мин)
- price (str): цена
""".strip()

    def _add_unique_by_product_name(
        self,
        target_list: list[dict[str, Any]],
        source_list: list[dict[str, Any]],
    ) -> None:
        """Добавить элементы из source_list, сохраняя уникальность по product_name."""
        existing_names = {
            item.get("product_name") for item in target_list if isinstance(item, dict)
        }

        for item in source_list:
            if not isinstance(item, dict):
                continue
            name = item.get("product_name")
            if name and name not in existing_names:
                target_list.append(item)
                existing_names.add(name)

    def _register_tool(self) -> FunctionTool:
        """Зарегистрировать MCP tool-функцию product_search."""

        @self.tool_product_search.tool(
            name="product_search",
            description=self.description,
        )
        async def product_search(
            session_id: str,
            query: str,
        ) -> Payload[list[dict[str, Any]]]:
            # Валидация
            if not session_id or not str(session_id).strip():
                return err(code="validation_error", error="session_id обязателен")

            if not query or not str(query).strip():
                # В query-only tool пустой query — это бессмысленно; возвращаем ok([]),
                # чтобы не ломать диалог, но можно сделать validation_error, если хотите жёстко.
                return ok([])

            logger.info(
                "[product_search] session_id=%s query=%r channel_ids=%s",
                session_id,
                query,
                self.channel_ids,
            )

            list_response: list[dict[str, Any]] = []
            any_channel_completed = False

            for channel_id in self.channel_ids:
                try:
                    response = await retriever_product_hybrid_async(
                        channel_id=channel_id,
                        query=query,
                    )
                    any_channel_completed = True
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "[product_search] channel_id=%s failed: %s", channel_id, exc
                    )
                    continue

                logger.info(
                    "[product_search] channel_id=%s response_len=%s",
                    channel_id,
                    len(response) if isinstance(response, list) else "n/a",
                )

                if isinstance(response, list):
                    self._add_unique_by_product_name(list_response, response)

            logger.info("[product_search] total_len=%s", len(list_response))

            # Итог:
            # - если хотя бы один канал отработал (даже вернул []) — ok(...)
            # - если все каналы упали исключениями — err
            if any_channel_completed:
                return ok(list_response)

            return err(code="internal_error", error="Ошибка поиска услуг")

        return product_search

    def get_tool(self) -> FastMCP:
        """Вернуть FastMCP-инструмент для монтирования."""
        return self.tool_product_search
