"""Универсальный клас создания mcp-сервера поиска услуг."""

from typing import Any

from fastmcp import FastMCP

from ..postgres.postgres_util import insert_dialog_state
from ..qdrant.retriever_product import retriever_product_hybrid_async


class MCPSearchProductQuery:
    """Универсальный клас создания mcp-сервера поиска услуг."""

    def __init__(self, channel_id: str) -> None:
        """Инициализация экземпляра класса mcp-сервера."""
        self.channel_id = channel_id
        self.tool_product_search = FastMCP(name="product_search")
        self._register_tool()

    def _register_tool(self):
        @self.tool_product_search.tool(
            name="product_search",
            description=(
                """
                Retrieve products based on query.

                Args:
                    query (str, optional): A free-text search query to match against product descriptions.
                    session_id(str): id dialog session.
                    channel_id(str): id channal company. 

                Returns:
                    List[dict]: A list of services, each represented by a dictionary with detailed metadata:
                        - product_id (str): Идентификатор продукта.
                        - product_name (str): Название продукта.
                        - duration (int): Продолжительность процедуры в минутах.
                        - price (str): Цена процедуры в денежном формате.
                """
            ),
        )
        async def product_search(
            channel_id: str,
            session_id: str,
            query: str,
        ) -> list[dict[str, Any]]:
            response = await retriever_product_hybrid_async(
                channel_id=self.channel_id,
                query=query,
            )

            insert_dialog_state(
                session_id=session_id,
                product_search={
                    "query_search": {"query": query},
                    "product_list": response,
                },
                name="selecting",
            )
            return response

    def get_tool(self) -> FastMCP:
        """Возвращаем сам FastMCP инструмент для монтирования."""
        return self.tool_product_search
