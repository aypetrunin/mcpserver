"""Универсальный клас создания mcp-сервера поиска услуг."""

from typing import Any
from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from ..postgres.postgres_util import insert_dialog_state  # type: ignore
from ..qdrant.retriever_common import logger  # type: ignore
from ..qdrant.retriever_product import retriever_product_hybrid_async  # type: ignore



class MCPSearchProductQuery:
    """Универсальный клас создания mcp-сервера поиска услуг."""

    def __init__(self, channel_ids: list[str]) -> None:
        """Инициализация экземпляра класса mcp-сервера."""
        self.channel_ids: str = channel_ids
        self.description:str = self._set_description()
        self.tool_product_search: FastMCP = FastMCP(name="product_search")
        self._register_tool()

    def get_description(self) -> str:
        """Функция возвращает описание для созданного инструмента."""
        return self.description

    def _set_description(self) -> str:
        """Функция делает описание для создаваемого инструмента."""
        
        description = """
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
        return description

    def _add_unique_by_product_name(self, target_list, source_list):
        existing_names = {item["product_name"] for item in target_list}

        for item in source_list:
            name = item.get("product_name")
            if name not in existing_names:
                target_list.append(item)
                existing_names.add(name)

        return target_list


    def _register_tool(self) -> FunctionTool:
        @self.tool_product_search.tool(
            name="product_search",
            description=self.description,
        )
        async def product_search(
            session_id: str,
            query: str,
        ) -> list[dict[str, Any]]:
            logger.info(f"\n\nЗапрос на 'product_search':\n'session_id': {session_id},\n'query': {query}\n")

            list_response = []
            for channel_id in self.channel_ids:
                response = await retriever_product_hybrid_async(
                    channel_id=channel_id,
                    query=query,
                ) 
                logger.info(f"\n\nОтвет от 'product_search(channel_id:{channel_id})':\n{response}\n")
            self._add_unique_by_product_name(list_response, response)

            insert_dialog_state(
                session_id=session_id,
                product_search={
                    "query_search": {"query": query},
                    "product_list": list_response,
                },
                name="selecting",
            )
            return list_response
        return product_search

    def get_tool(self) -> FastMCP:
        """Возвращаем сам FastMCP инструмент для монтирования."""
        return self.tool_product_search


if __name__=="__main__":
    mcp = MCPSearchProductQuery(channel_id='1')
    print(mcp.get_description())


# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.tools.class_product_search_query