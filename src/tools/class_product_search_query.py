"""Универсальный класс создания MCP-сервера поиска услуг."""

import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from ..qdrant.retriever_product import retriever_product_hybrid_async  # type: ignore


logger = logging.getLogger(__name__)


class MCPSearchProductQuery:
    """Универсальный класс создания MCP-сервера поиска услуг."""

    def __init__(self, channel_ids: list[str]) -> None:
        """Инициализировать MCP-инструмент поиска услуг по текстовому запросу."""
        self.channel_ids: list[str] = channel_ids
        self.description: str = self._set_description()
        self.tool_product_search: FastMCP = FastMCP(name="product_search")
        self._register_tool()

    def get_description(self) -> str:
        """Вернуть description для созданного инструмента."""
        return self.description

    def _set_description(self) -> str:
        """Сформировать description (инструкцию) для LLM."""
        return """
Retrieve products based on query.

Args:
    session_id (str): ID dialog session.
    query (str): A free-text search query to match against product descriptions.

Returns:
    List[dict]: A list of services, each represented by a dictionary with metadata:
        - product_id (str): Идентификатор продукта.
        - product_name (str): Название продукта.
        - duration (int): Продолжительность процедуры в минутах.
        - price (str): Цена процедуры в денежном формате.
""".strip()

    def _add_unique_by_product_name(
        self,
        target_list: list[dict[str, Any]],
        source_list: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Добавить элементы из source_list, сохраняя уникальность по product_name."""
        existing_names = {item.get("product_name") for item in target_list}

        for item in source_list:
            name = item.get("product_name")
            if name and name not in existing_names:
                target_list.append(item)
                existing_names.add(name)

        return target_list

    def _register_tool(self) -> FunctionTool:
        """Зарегистрировать MCP tool-функцию product_search."""
        @self.tool_product_search.tool(
            name="product_search",
            description=self.description,
        )
        async def product_search(
            session_id: str,
            query: str,
        ) -> list[dict[str, Any]]:
            logger.info(
                "[product_search] session_id=%s query=%s channel_ids=%s",
                session_id,
                query,
                self.channel_ids,
            )

            list_response: list[dict[str, Any]] = []

            for channel_id in self.channel_ids:
                response = await retriever_product_hybrid_async(
                    channel_id=channel_id,
                    query=query,
                )
                logger.info(
                    "[product_search] channel_id=%s response_len=%s",
                    channel_id,
                    len(response),
                )
                self._add_unique_by_product_name(list_response, response)

            logger.info(
                "[product_search] total_len=%s",
                len(list_response),
            )
            return list_response

        return product_search

    def get_tool(self) -> FastMCP:
        """Вернуть FastMCP-инструмент для монтирования."""
        return self.tool_product_search
