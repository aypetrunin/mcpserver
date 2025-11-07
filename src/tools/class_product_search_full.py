from typing import Any
from fastmcp import FastMCP
from ..postgres.postgres_util import insert_dialog_state, select_key
from ..qdrant.retriever_product import retriever_product_hybrid_async


class MCPServiceFull:
    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.key = select_key(channel_id=int(channel_id))
        self.tool_product_search = FastMCP(name="product_search")
        self._register_tool()

    def _get_description(self) -> str:
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
            "product_type": [],,
            "session_id": "1-232327692"
        }}

    Пример 2: Клиент: "У меня редкие волосы на бровях, что можете предложить?"
        Вход: query_search = 
        {{
            "query": "",
            "indications": ["редкие"],
            "contraindications": [],
            "body_parts": ["брови, волосы"],
            "product_type": [],,
            "session_id": "1-232327692"
        }}

    Пример 3: Клиент: "Что у Вас есть для лица?", "А что есть для лица?", "Что можете предложить для лица", "Нужно что-то сделать с лицом"
        Вход: query_search = 
        {{
            "query": "",
            "indications": [],
            "contraindications": [],
            "body_parts": ["лицо"],
            "product_type": [],,
            "session_id": "1-232327692"
        }}

    Пример 4: Клиент: "Можно записаться на консультацию?", "У вас есть консультация?"
        Вход: query_search = 
        {{
            "query": "консультация",
            "indications": [],
            "contraindications": [],
            "body_parts": [],,
            "session_id": "1-232327692"
        }}

    Пример 5: Клиент: "Есть ли услуги для коррекции фигуры?"
        Вход: query_search = 
        {{
            "query": "",
            "indications": ["коррекция фигуры"],
            "contraindications": [],
            "body_parts": [],
            "product_type": [],,
            "session_id": "1-232327692"
        }}

    Пример 6: Клиент: "Нужна эпиляция волос подмышками?"
        Вход: query_search = 
        {{
            "query": "эпиляция",
            "indications": ["волосы"],
            "contraindications": [],
            "body_parts": ["подмышки"],,
            "session_id": "1-232327692"
        }}

    Пример 7: Клиент: "У Вас есть акции на услуги?"
        Вход: query_search = 
        {{
            "query": "акции",
            "indications": [],
            "contraindications": [],
            "body_parts": [],
            "session_id": "1-232327692"
        }}
    
    Пример 8: Клиент: "Какие есть комплексы для коррекции фигуры"
        Вход: query_search = 
        {{
            "query": "комплексы",
            "indications": [коррекция фигуры],
            "contraindications": [],
            "body_parts": [],
            "session_id": "1-232327692"
        }}

    Пример 9: Клиент: "Можно записаться на консультацию"
        Вход: query_search = 
        {{
            "query": "консультация",
            "indications": [],
            "contraindications": [],
            "body_parts": [],
            "session_id": "1-232327692"
        }}

    Args:
        query (str, optional): A free-text search query to match against product descriptions.
        
        indications (List[str], optional): A list of positive indications (symptoms or cosmetic needs).
            Only the following values are allowed: {self.key['indications_key']}

        contraindications (List[str], optional): A list of negative indications to exclude.
            Only the following values are allowed: {self.key['contraindications_key']}

        body_parts (List[str], optional): A list of body parts to be treated/serviced.
            Only the following values are allowed: {self.key['body_parts']}

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

    def _register_tool(self):
        @self.tool_product_search.tool(
            name="product_search",
            description=self._get_description(),
        )
        async def product_search(
            session_id: str,
            query: str | None = None,
            indications: list[str] | None = None,
            contraindications: list[str] | None = None,
            body_parts: list[str] | None = None,
        ) -> list[dict[str, Any]]:
            response = await retriever_product_hybrid_async(
                channel_id=self.channel_id,
                query=query,
                indications=indications,
                contraindications=contraindications,
                body_parts=body_parts,
            )
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

    def get_tool(self) -> FastMCP:
        # Возвращаем сам FastMCP инструмент для монтирования
        return self.tool_product_search
