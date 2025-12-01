"""Универсальный клас создания mcp-сервера поиска услуг."""

from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from ..postgres.postgres_util import insert_dialog_state, select_key  # type: ignore
from ..qdrant.retriever_product import retriever_product_hybrid_async  # type: ignore
from ..qdrant.retriever_common import logger  # type: ignore


class MCPSearchProductFull:
    """Универсальный клас создания mcp-сервера поиска услуг."""

    def __init__(self, channel_id: str) -> None:
        """Инициализация экземпляра класса mcp-сервера."""
        self.channel_id: str = channel_id
        self.key: dict[str, Any] = select_key(channel_id=int(channel_id))
        self.description: str = self._set_description()
        self.tool_product_search: FastMCP = FastMCP(name="product_search")
        self._register_tool()

    def _set_description(self) -> str:
        description = f"""
    Retrieve.

    Retrieve products based on query and optional indications, contraindications, body parts and product_type.
    Follow the lists exactly when generating a search query by parameters: indications, contraindications, body parts and product_type.
    Pick only one similar symptoms or cosmetic needs for one indication or contraindication.

    Пример 1: Клиент: "Мне нужен массаж чтобы убрать отечность ног, но у меня варикозная болезнь"
        Вход: query_search = 
        {{
            "query": "массаж",
            "indications": ["отечность"],
            "contraindications": ["варикоз"],
            "body_parts": ["ноги"],
            "session_id": "1-232327692"
        }}

    Пример 2: Клиент: "У меня редкие волосы на бровях, что можете предложить?"
        Вход: query_search = 
        {{
            "query": "",
            "indications": ["редкие"],
            "contraindications": [],
            "body_parts": ["брови, волосы"],
            "session_id": "1-232327692"
        }}

    Пример 3: Клиент: "Что у Вас есть для лица?", "А что есть для лица?", "Что можете предложить для лица", "Нужно что-то сделать с лицом"
        Вход: query_search = 
        {{
            "query": "",
            "indications": [],
            "contraindications": [],
            "body_parts": ["лицо"],
            "session_id": "1-232327692",
        }}

    Пример 4: Клиент: "Можно записаться на консультацию?", "У вас есть консультация?"
        Вход: query_search = 
        {{
            "query": "консультация",
            "indications": [],
            "": [],
            "body_parts": [],,
            "session_id": "1-232327692",
        }}

    Пример 5: Клиент: "Есть ли услуги для коррекции фигуры?"
        Вход: query_search = 
        {{
            "query": "",
            "indications": ["коррекция фигуры"],
            "contraindications": [],
            "body_parts": [],
            "product_type": [],,
            "session_id": "1-232327692",
        }}

    Пример 6: Клиент: "Нужна эпиляция волос подмышками?"
        Вход: query_search = 
        {{
            "query": "эпиляция",
            "indications": ["волосы"],
            "contraindications": [],
            "body_parts": ["подмышки"],,
            "session_id": "1-232327692",
        }}

    Пример 7: Клиент: "У Вас есть акции на услуги?"
        Вход: query_search = 
        {{
            "query": "акции",
            "indications": [],
            "contraindications": [],
            "body_parts": [],
            "session_id": "1-232327692",
        }}
    
    Пример 8: Клиент: "Какие есть комплексы для коррекции фигуры"
        Вход: query_search = 
        {{
            "query": "комплексы",
            "indications": [коррекция фигуры],
            "contraindications": [],
            "body_parts": [],
            "session_id": "1-232327692",
            
        }}

    Пример 9: Клиент: "Можно записаться на консультацию"
        Вход: query_search = 
        {{
            "query": "консультация",
            "indications": [],
            "contraindications": [],
            "body_parts": [],
            "session_id": "1-232327692",
        }}

    Args:
        query (str, optional): A free-text search query to match against product descriptions.
        
        indications (List[str], optional): A list of positive indications (symptoms or cosmetic needs). \
Only the following values from the list are allowed: [{self.key.get("indications_key", "Нет данных")}]

        contraindications (List[str], optional): A list of negative indications to exclude. \
Only the following values from the list are allowed: [{self.key.get("contraindications_key", "Нет данных")}]

        body_parts (List[str], optional): A list of body parts to be treated/serviced. \
Only the following values from the list are allowed: [{self.key.get("body_parts", "Нет данных.")}]

        session_id(str): id dialog session.

    Returns:
        List[dict]: A list of services, each represented by a dictionary with detailed metadata:
            - product_id (str): Идентификатор продукта.
            - product_name (str): Название продукта.
            - duration (int): Продолжительность процедуры в минутах.
            - price (str): Цена процедуры в денежном формате.
    """
        return description

    def _register_tool(self) -> FunctionTool:
        @self.tool_product_search.tool(
            name="product_search",
            description=self.description,
        )
        async def product_search(
            session_id: str,
            query: str | None = None,
            indications: list[str] | None = None,
            contraindications: list[str] | None = None,
            body_parts: list[str] | None = None,
        ) -> list[dict[str, Any]]:
            logger.info(f"\n\nЗапрос на 'product_search':\n'session_id': {session_id},\n'query': \
{query},\n'body_parts': {body_parts},\n'indications': {indications},\n'contraindications': {contraindications}\n")
            response = await retriever_product_hybrid_async(
                channel_id=self.channel_id,
                query=query,
                indications=indications,
                contraindications=contraindications,
                body_parts=body_parts,
            )
            logger.info(f"\n\nОтвет от 'product_search':\n{response}\n")
            insert_dialog_state(
                session_id=session_id,
                product_search={
                    "query_search": {
                        "query": query,
                        "indications": indications,
                        "contraindications": contraindications,
                        "body_parts": body_parts,
                    },
                    "product_list": response,
                },
                name="selecting",
            )
            return response
        return product_search

    def get_tool(self) -> FastMCP:
        """Возвращаем сам FastMCP инструмент для монтирования."""
        return self.tool_product_search

    def get_description(self) -> str:
        """Возвращаем сам FastMCP инструмент для монтирования."""
        return self.description


if __name__=="__main__":
    mcp = MCPSearchProductFull(channel_id='5')
    print(mcp.get_description())


# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.tools.class_product_search_full