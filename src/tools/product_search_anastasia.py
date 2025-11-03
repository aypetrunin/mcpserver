"""MCP-сервер поиска услуг специфичных для фирмы Анастасия."""

from typing import Any

from fastmcp import FastMCP

from ..postgres.postgres_util import insert_dialog_state

# from ..qdrant.retriver_product import retriever_product_hybrid_mult_async
from ..qdrant.retriever_product import retriever_product_hybrid_async

tool_product_search = FastMCP(name="product_search")


@tool_product_search.tool(
    name="product_search",
    description=(
        """
    Retrieve.

    Retrieve products based on query and optional indications, contraindications, body parts and product_type.

    Follow the lists exactly when generating a search query by parameters: indications, contraindications, body parts and product_type.
    Pick only one similar symptoms or cosmetic needs for one indication or contraindication.

    Пример 1: Клиент: "Мне нужен массаж чтобы убрать отечность ног, но у меня варикозная болезнь"
          Вход: 
          query_search = 
          {
            "query": "массаж",
            "indications": ["отечность"],
            "contraindications": ["варикоз"],
            "body_parts": ["ноги"],
            "product_type": [],
            "session_id": "1_232327692"
          }

    Пример 2: Клиент: "У меня редкие волосы на бровях, что можете предложить?"
          Вход: 
          query_search = 
          {
            "query": "",
            "indications": ["редкие"],
            "contraindications": [],
            "body_parts": ["брови, волосы"],
            "product_type": [],
            "session_id": "1_232327692"
          }

    Пример 3: Клиент: "Что у Вас есть для лица?", "А что есть для лица?", "Что можете предложить для лица", "Нужно что-то сделать с лицом"
          Вход: 
          query_search = 
          {
            "query": "",
            "indications": [],
            "contraindications": [],
            "body_parts": ["лицо"],
            "product_type": [],
            "session_id": "1_232327692"
          }

    Пример 4: Клиент: "Можно записаться на консультацию"
          Вход: 
          query_search = 
          {
            "query": "консультация",
            "indications": [],
            "contraindications": [],
            "body_parts": [],
            "session_id": "1_232327692"
          }
    Args:
        query (str, optional): A free-text search query to match against product descriptions.

        indications (List[str], optional): A list of positive indications (symptoms or cosmetic needs).
            Only the following values are allowed:
            "целлюлит", "отечность", "жировые отложения", "потеря упругости", "нарушение баланса", "застой лимфы", "коррекция фигуры",
            "нарушение микроциркуляции", "улучшение метаболизма", "дряблость", "снижение тонуса мышц", "нарушение кровообращения",
            "атрофия мышц", "нарушение работы сальных желез", "улучшение микроциркуляции"


        contraindications (List[str], optional): A list of negative indications to exclude.
            Only the following values are allowed:
            "онкология", "тромбоз", "тромбофлебит", "экзема", "сосудистые заболевания", "кардиостимулятор", "протезы", "почечная недостаточность",
            "печёночная недостаточность", "мочекаменная болезнь", "диабет", "гипертония", "беременность", "лактация", "менструация", "воспаление",
            "температура", "щитовидка", "острые травмы", "гипотония", "нарушение кровообращения", "инфекция", "нарушения ритма", "варикоз", "эпилепсия"


        body_parts (List[str], optional): A list of body parts to be treated/serviced.
            Only the following values are allowed:
            "тело", "ноги", "руки", "ягодицы", "живот", "бедра", "спина"


        session_id(str): id dialog session.

        channel_id(str): id channal company. 

        Returns:
            List[dict]: A list of services, each represented by a dictionary with detailed metadata:
                - product_id (str): Идентификатор продукта.
                - product_name (str): Название продукта.
                - body_parts (str): Части тела.
                - product_type (str): Формат обслуживания.
                - product_description (str): Описание процедуры или продукта.
                - duration (int): Продолжительность процедуры в минутах.
                - price (str): Цена процедуры в денежном формате.
    """
    ),
)
async def product_search(
    channel_id: str,
    session_id: str,
    query: str | None = None,
    indications: list[str] | None = None,
    contraindications: list[str] | None = None,
    product_type: list[str] | None = None,
    body_parts: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Функция гибридного поиска услуг с фильтрацией."""
    responce = await retriever_product_hybrid_async(
        channel_id=channel_id,
        query=query,
        indications=indications,
        contraindications=contraindications,
        body_parts=body_parts,
        # product_type=product_type,
    )

    insert_dialog_state(
        session_id=session_id,
        product_search={
            "query_search": {
                "query": query,
                "indications": indications,
                "contraindications": contraindications,
                "body_parts": body_parts,
                # "product_type": product_type,
            },
            "product_list": responce,
        },
        name="selecting",
    )

    return responce
