"""MCP-сервер поиска услуг специфичных для фирмы София."""

from typing import Any

from fastmcp import FastMCP

from ..postgres.postgres_util import insert_dialog_state, select_key
from ..qdrant.retriever_product import (
    retriever_product_hybrid_async,
)


key = select_key(channel_id=1)

tool_product_search = FastMCP(name="product_search")

@tool_product_search.tool(
    name="product_search",
    description=(
        f"""
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
        }

    Пример 4: Клиент: "Можно записаться на консультацию"
        Вход: 
        query_search = 
        {
        "query": "консультация",
        "indications": [],
        "contraindications": [],
        "body_parts": [],
        }

    Args:
        query (str, optional): A free-text search query to match against product descriptions.

        indications (List[str], optional): A list of positive indications (symptoms or cosmetic needs).
            Only the following values are allowed:
            "акне", "брыли", "варикоз", "возрастные изменения", "воспаления", "восстановление", "восстановление после операций",
            "восстановление после похудения", "восстановление после родов", "жировая прослойка", "жировой тип", "жировые ловушки",
            "жировые отложения", "жирная кожа", "живот", "загрязнения", "заломы", "замедленное кровообращение",
            "замедленный лимфообращение", "замедленный метаболизм", "застой лимфы", "застойные пятна", "избыточный жир",
            "комедоны", "комбинированная кожа", "контур подбородка", "контурная коррекция", "коррекция фигуры", "купероз",
            "лимфостаз", "липодистрофия", "локальный жир", "мешки", "мимические морщины", "моделирование", "морщины", "напряжение"
            "напряжение мышц", "неровный рельеф", "неровный цвет", "носогубные складки", "обвисание кожи", "обезвоженность",
            "омоложение", "опущение", "отечность", "пигментация", "пигментные пятна", "плохой лимфоток", "постакне",
            "провисание кожи", "прыщи", "подготовка к операциям", "подготовка к процедурам", "подготовка кожи", "рубцы",
            "розацеа", "растяжки", "реабилитация", "расширенные поры", "снижение тонуса", "снижение тургора", "снижение упругости",
            "сидячая работа", "синяки", "складки", "слабый кровоток", "стресс", "сухая кожа", "сухость", "судороги",
            "стареющая кожа", "тугой тургор", "тусклый цвет", "точки", "усталость", "усталость кожи", "усталость мышц",
            "уход", "физическая нагрузка", "фланки", "целлюлит", "чувствительная кожа", "шелушение", "эластичность"



        contraindications (List[str], optional): A list of negative indications to exclude.
            Only the following values are allowed:
            "аллергия", "аллергия водоросли", "аутоиммунные заболевания", "беременность", "болезни крови", "ботокс", "варикоз",
            "воспаление", "воспаления", "гематомы", "гипертония", "гнойничковые высыпания", "гнойные воспаления", "грыжа", "дерматит",
            "дерматологические патологии", "диабет", "заболевания щитовидной", "герпес", "герпетическая сыпь", "импланты", "инфекция",
            "инъекции", "кардиостимулятор", "кашель", "клаустрофобия", "кожные заболевания", "кожные инфекции", "конъюнктивит",
            "крапивница", "кровоподтеки", "купероз", "лактация", "лазерные процедуры", "лимфатические заболевания",
            "нарушение чувствительности", "нарушения свертываемости", "насморк", "неврологические расстройства", "нити", "онкология",
            "ожоги", "опухоли", "ОРВИ", "ОРЗ", "остеопороз", "открытые раны", "патологии шеи", "печёночная недостаточность",
            "повреждение кожи", "повреждения кожи", "психические заболевания", "протезы", "простуда", "родинки множественные",
            "светочувствительность", "сосудистая сетка", "сосудистые заболевания", "ссадины", "температура", "тромбоз", "тромбофлебит",
            "ушибы", "эпилепсия", "щитовидка", "химический пилинг", "фотосенсибилизирующие препараты"



        body_parts (List[str], optional): A list of body parts to be treated/serviced.
            Only the following values are allowed:
            "бедра", "веки", "второй подбородок", "декольте", "живот", "лицо", "ноги", "носогубные складки", "подбородок",
            "руки", "спина", "шейно-воротниковая зона", "шея", "щеки", "ягодицы"


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
    body_parts: list[str] | None = None,
    # product_type: list[str] | None = None,
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
