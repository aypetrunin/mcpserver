# class_product_search_full.py

"""Универсальный клас создания mcp-сервера поиска услуг."""

from __future__ import annotations

import textwrap
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from ..postgres.postgres_util import select_key  # type: ignore
from ..qdrant.retriever_common import logger  # type: ignore
from ..qdrant.retriever_product import retriever_product_hybrid_async  # type: ignore


class MCPSearchProductFull:
    """Универсальный клас создания mcp-сервера поиска услуг."""

    def __init__(self, channel_ids: list[str], key: dict[str, Any]) -> None:
        """СИНХРОННАЯ часть инициализации: ключи уже должны быть загружены."""
        self.channel_ids: list[str] = channel_ids
        self.key: dict[str, Any] = key  # <-- гарантированно dict, не coroutine

        self.description: str = self._set_description()
        self.tool_product_search: FastMCP = FastMCP(name="product_search")
        self._register_tool()

    @classmethod
    async def create(cls, channel_ids: list[str]) -> "MCPSearchProductFull":
        channel_id = int(channel_ids[0])
        key = await select_key(channel_id=channel_id)
        if not key:
            raise RuntimeError(
                f"Нет сервисных ключей для channel_id={channel_id}. "
                "Проверьте view_channel_services_keys / env / channel_ids."
            )
        return cls(channel_ids=channel_ids, key=key)

    def _pretty_list(self, raw: Any) -> str:
        if not raw:
            return "Нет данных"
        if isinstance(raw, str):
            items = [x.strip().strip('"') for x in raw.split(",")]
            items = [x for x in items if x]  # убираем пустые
            return ", ".join(items)
        if isinstance(raw, list):
            items = [str(x).strip() for x in raw if str(x).strip()]
            return ", ".join(items)
        return str(raw)

    def _pretty_list_multiline(self, raw: Any, per_line: int = 10) -> str:
        """
        Форматирует список значений в многострочный вид:
        - убирает пустые элементы
        - убирает кавычки
        - разбивает по строкам (per_line значений в строке)
        - добавляет '-' в начале каждой строки (внутри массива)
        """
        if not raw:
            return "  - нет данных -"

        if isinstance(raw, str):
            items = [x.strip().strip('"') for x in raw.split(",")]
        elif isinstance(raw, list):
            items = [str(x).strip() for x in raw]
        else:
            return str(raw)

        # убираем пустые элементы
        items = [x for x in items if x]

        lines = []
        for i in range(0, len(items), per_line):
            chunk = items[i : i + per_line]
            lines.append("  - " + ", ".join(chunk))

        # ВАЖНО:
        # здесь НЕ добавляем дополнительных пробелов,
        # отступ задаётся в шаблоне description перед вставкой
        return "\n".join(lines)


    def _set_description(self) -> str:
        description = textwrap.dedent(f"""
Поиск услуг

Поиск услуг на основе запроса и дополнительных параметров:
indications (показания), contraindications (противопоказания), body_parts (части тела).

ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:
- Используй ТОЛЬКО точные значения из списков ниже.
- НИКОГДА не придумывай новые значения и не изменяй формулировки.
- Если точного совпадения нет:
    - Сначала подбери наиболее подходящее значение СТРОГО из списка ниже,
        исходя из семантического смысла запроса пользователя.
    - Если ни одно значение из списка не подходит по смыслу —
        верни пустой список [].
- indications: максимум 2 значения.
- contraindications: максимум 2 значения.
- body_parts: максимум 2 значения.
- Если одно и то же значение подходит и для indications, и для contraindications — предпочитай indications.
- Если пользователь упоминает процедуру или тип услуги(массаж, эпиляция, консультация, акции, комплексы) помести это в поле "query".
- Если query пустой, заполни хотя бы один из списков (indications или body_parts), иначе оставь query непустым.
- indications — ТОЛЬКО симптомы или косметические задачи.
- session_id обязателен.
- Строго следуй спискам при формировании параметров.

────────────────────
ПРИМЕРЫ
────────────────────

Пример 1: Клиент: «Мне нужен массаж, чтобы убрать отечность ног, но у меня варикоз»
Вход:
{{
    "query": "массаж",
    "indications": ["отечность"],
    "contraindications": ["варикоз"],
    "body_parts": ["ноги"],
    "session_id": "1-232327692"
}}

Пример 2: Клиент: «У меня редкие волосы на бровях, что можете предложить?»
Вход:
{{
    "query": "",
    "indications": ["редкие"],
    "contraindications": [],
    "body_parts": ["брови", "волосы"],
    "session_id": "1-232327692"
}}

Пример 3: Клиент: «Что у вас есть для лица?»
Вход:
{{
    "query": "",
    "indications": [],
    "contraindications": [],
    "body_parts": ["лицо"],
    "session_id": "1-232327692"
}}

Пример 4: Клиент: «Можно записаться на консультацию?»
Вход:
{{
    "query": "консультация",
    "indications": [],
    "contraindications": [],
    "body_parts": [],
    "session_id": "1-232327692"
}}

Пример 5: Клиент: «Есть ли услуги для коррекции фигуры?»
Вход:
{{
    "query": "",
    "indications": ["коррекция фигуры"],
    "contraindications": [],
    "body_parts": [],
    "session_id": "1-232327692"
}}

Пример 6: Клиент: «Нужна эпиляция волос в подмышках»
Вход:
{{
    "query": "эпиляция",
    "indications": ["волосы"],
    "contraindications": [],
    "body_parts": ["подмышки"],
    "session_id": "1-232327692"
}}

Пример 7: Клиент: «У вас есть акции на услуги?»
Вход:
{{
    "query": "акции",
    "indications": [],
    "contraindications": [],
    "body_parts": [],
    "session_id": "1-232327692"
}}

Пример 8: Клиент: «Какие есть комплексы для коррекции фигуры?»
Вход:
{{
    "query": "комплексы",
    "indications": ["коррекция фигуры"],
    "contraindications": [],
    "body_parts": [],
    "session_id": "1-232327692"
}}

────────────────────
ПАРАМЕТРЫ
────────────────────

query (str, необязательно):
Свободный текст с названием процедуры или услуги.

indications (List[str], необязательно):
Положительные показания (симптомы или косметические задачи).
Допустимые значения:
[
{self._pretty_list_multiline(self.key.get("indications_key"))}
]

contraindications (List[str], необязательно):
Противопоказания.
Допустимые значения:
[
{self._pretty_list_multiline(self.key.get("contraindications_key"))}
]

body_parts (List[str], необязательно):
Части тела, для которых подбирается услуга.
Допустимые значения:
[
{self._pretty_list_multiline(self.key.get("body_parts"))}
]

session_id (str):
Идентификатор диалога.

────────────────────
РЕЗУЛЬТАТ
────────────────────

List[dict]:
Список услуг, каждая услуга содержит:
- product_id (str): идентификатор услуги
- product_name (str): название услуги
- duration (int): длительность в минутах
- price (str): цена
""")
        return description


    def _set_description_old(self) -> str:
        description = f"""
Retrieve.

Retrieve products based on query and optional indications, contraindications, body parts.
Follow the lists exactly when generating a search query by parameters: indications, contraindications, body parts.
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
            "body_parts": ["брови", "волосы"],
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
            "contraindications": [],
            "body_parts": [],
            "session_id": "1-232327692",
        }}

    Пример 5: Клиент: "Есть ли услуги для коррекции фигуры?"
        Вход: query_search = 
        {{
            "query": "",
            "indications": ["коррекция фигуры"],
            "contraindications": [],
            "body_parts": [],
            "session_id": "1-232327692",
        }}

    Пример 6: Клиент: "Нужна эпиляция волос подмышками?"
        Вход: query_search = 
        {{
            "query": "эпиляция",
            "indications": ["волосы"],
            "contraindications": [],
            "body_parts": ["подмышки"],
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
            "indications": ["коррекция фигуры"],
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

    indications (List[str], optional): A list of positive indications (symptoms or cosmetic needs).
        Only the following values from the list are allowed: [{self._pretty_list(self.key.get("indications_key"))}]

    contraindications (List[str], optional): A list of negative indications to exclude.
        Only the following values from the list are allowed: [{self._pretty_list(self.key.get("contraindications_key"))}]

    body_parts (List[str], optional): A list of body parts to be treated/serviced.
        Only the following values from the list are allowed: [{self._pretty_list(self.key.get("body_parts"))}]

    session_id(str): id dialog session.

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
            query: str | None = None,
            indications: list[str] | None = None,
            contraindications: list[str] | None = None,
            body_parts: list[str] | None = None,
        ) -> list[dict[str, Any]]:
            logger.info(
                f"\n\n channel_ids: {self.channel_ids}. Запрос на 'product_search':\n"
                f"'session_id': {session_id},\n'query': {query},\n'body_parts': {body_parts},\n"
                f"'indications': {indications},\n'contraindications': {contraindications}\n"
            )

            list_response = []
            for channel_id in self.channel_ids:
                response = await retriever_product_hybrid_async(
                    channel_id=channel_id,
                    query=query,
                    indications=indications,
                    contraindications=contraindications,
                    body_parts=body_parts,
                )
                logger.info(f"Ответ от 'product_search(channel_id:{channel_id})':\n{response}\n")
                logger.info(f"Количество 'product_search(channel_id:{channel_id})':{len(response)}\n")
                self._add_unique_by_product_name(list_response, response)

            logger.info(f"ИТОГО количество 'product_search(channel_ids:{self.channel_ids})':{len(list_response)}\n")
            return list_response

        return product_search

    def get_tool(self) -> FastMCP:
        """Возвращаем сам FastMCP инструмент для монтирования."""
        return self.tool_product_search

    def get_description(self) -> str:
        return self.description


if __name__ == "__main__":

    import asyncio
    from ..postgres.db_pool import get_pg_pool, init_pg_pool, close_pg_pool
    from src.runtime import init_runtime

    async def _main():
        init_runtime()
        await init_pg_pool()
        mcp = await MCPSearchProductFull.create(channel_ids=["1"])
        print(mcp.get_description())

    asyncio.run(_main())



# import os

# from ..postgres.db_pool import get_pg_pool, init_pg_pool, close_pg_pool
# from src.runtime import init_runtime


# if __name__ == "__main__":
#     """
#     Ручной запуск из консоли.

#     Важно:
#     - Здесь мы запускаем отдельный процесс, поэтому сами:
#       1) загружаем env (init_runtime)
#       2) создаём пул (init_pg_pool)
#       3) вызываем нужную функцию
#       4) закрываем пул (close_pg_pool)
#     """

#     import asyncio
#     from ..postgres.db_pool import get_pg_pool, init_pg_pool, close_pg_pool
#     from src.runtime import init_runtime
#     async def _demo() -> None:
#         init_runtime()
#         await init_pg_pool()
#         try:
#             # Выбирай что нужно:
#             # await create_view_channel_services_keys()
#             await create_product_service_view()
#             # или:
#             # await create_all_views()
#             print("OK: views updated")
#         finally:
#             await close_pg_pool()

#     asyncio.run(_demo())




# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.tools.class_product_search_full


# """Универсальный клас создания mcp-сервера поиска услуг."""

# from typing import Any

# from fastmcp import FastMCP
# from fastmcp.tools import FunctionTool

# from ..postgres.postgres_util import select_key  # type: ignore
# from ..qdrant.retriever_common import logger  # type: ignore
# from ..qdrant.retriever_product import retriever_product_hybrid_async  # type: ignore

# class MCPSearchProductFull:
#     """Универсальный клас создания mcp-сервера поиска услуг."""

#     def __init__(self, channel_ids: list[str]) -> None:
#         """Инициализация экземпляра класса mcp-сервера."""
#         self.channel_ids: list[str] = channel_ids
#         self.key: dict[str, Any] = select_key(channel_id=int(channel_ids[0]))
#         self.description: str = self._set_description()
#         self.tool_product_search: FastMCP = FastMCP(name="product_search")
#         self._register_tool()

#     def _set_description(self) -> str:
#         description = f"""
#     Retrieve.
 
#     Retrieve products based on query and optional indications, contraindications, body parts.
#     Follow the lists exactly when generating a search query by parameters: indications, contraindications, body parts.
#     Pick only one similar symptoms or cosmetic needs for one indication or contraindication.

#     Пример 1: Клиент: "Мне нужен массаж чтобы убрать отечность ног, но у меня варикозная болезнь"
#         Вход: query_search = 
#         {{
#             "query": "массаж",
#             "indications": ["отечность"],
#             "contraindications": ["варикоз"],
#             "body_parts": ["ноги"],
#             "session_id": "1-232327692"
#         }}

#     Пример 2: Клиент: "У меня редкие волосы на бровях, что можете предложить?"
#         Вход: query_search = 
#         {{
#             "query": "",
#             "indications": ["редкие"],
#             "contraindications": [],
#             "body_parts": ["брови", "волосы"],
#             "session_id": "1-232327692"
#         }}

#     Пример 3: Клиент: "Что у Вас есть для лица?", "А что есть для лица?", "Что можете предложить для лица", "Нужно что-то сделать с лицом"
#         Вход: query_search = 
#         {{
#             "query": "",
#             "indications": [],
#             "contraindications": [],
#             "body_parts": ["лицо"],
#             "session_id": "1-232327692",
#         }}

#     Пример 4: Клиент: "Можно записаться на консультацию?", "У вас есть консультация?"
#         Вход: query_search = 
#         {{
#             "query": "консультация",
#             "indications": [],
#             "contraindications": [],
#             "body_parts": [],
#             "session_id": "1-232327692",
#         }}

#     Пример 5: Клиент: "Есть ли услуги для коррекции фигуры?"
#         Вход: query_search = 
#         {{
#             "query": "",
#             "indications": ["коррекция фигуры"],
#             "contraindications": [],
#             "body_parts": [],
#             "session_id": "1-232327692",
#         }}

#     Пример 6: Клиент: "Нужна эпиляция волос подмышками?"
#         Вход: query_search = 
#         {{
#             "query": "эпиляция",
#             "indications": ["волосы"],
#             "contraindications": [],
#             "body_parts": ["подмышки"],,
#             "session_id": "1-232327692",
#         }}

#     Пример 7: Клиент: "У Вас есть акции на услуги?"
#         Вход: query_search = 
#         {{
#             "query": "акции",
#             "indications": [],
#             "contraindications": [],
#             "body_parts": [],
#             "session_id": "1-232327692",
#         }}
    
#     Пример 8: Клиент: "Какие есть комплексы для коррекции фигуры"
#         Вход: query_search = 
#         {{
#             "query": "комплексы",
#             "indications": ["коррекция фигуры"],
#             "contraindications": [],
#             "body_parts": [],
#             "session_id": "1-232327692",
            
#         }}

#     Пример 9: Клиент: "Можно записаться на консультацию"
#         Вход: query_search = 
#         {{
#             "query": "консультация",
#             "indications": [],
#             "contraindications": [],
#             "body_parts": [],
#             "session_id": "1-232327692",
#         }}

#     Args:
#         query (str, optional): A free-text search query to match against product descriptions.
        
#         indications (List[str], optional): A list of positive indications (symptoms or cosmetic needs). \
# Only the following values from the list are allowed: [{self.key.get("indications_key", "Нет данных")}]

#         contraindications (List[str], optional): A list of negative indications to exclude. \
# Only the following values from the list are allowed: [{self.key.get("contraindications_key", "Нет данных")}]

#         body_parts (List[str], optional): A list of body parts to be treated/serviced. \
# Only the following values from the list are allowed: [{self.key.get("body_parts", "Нет данных.")}]

#         session_id(str): id dialog session.

#     Returns:
#         List[dict]: A list of services, each represented by a dictionary with detailed metadata:
#             - product_id (str): Идентификатор продукта.
#             - product_name (str): Название продукта.
#             - duration (int): Продолжительность процедуры в минутах.
#             - price (str): Цена процедуры в денежном формате.
#     """
#         return description

#     def _add_unique_by_product_name(self, target_list, source_list):
#         existing_names = {item["product_name"] for item in target_list}

#         for item in source_list:
#             name = item.get("product_name")
#             if name not in existing_names:
#                 target_list.append(item)
#                 existing_names.add(name)

#         return target_list


#     def _register_tool(self) -> FunctionTool:
#         @self.tool_product_search.tool(
#             name=f"product_search",
#             description=self.description,
#         )
#         async def product_search(
#             session_id: str,
#             query: str | None = None,
#             indications: list[str] | None = None,
#             contraindications: list[str] | None = None,
#             body_parts: list[str] | None = None,
#         ) -> list[dict[str, Any]]:
#             logger.info(f"\n\n channel_ids: {self.channel_ids}. Запрос на 'product_search':\n'session_id': {session_id},\n'query': \
# {query},\n'body_parts': {body_parts},\n'indications': {indications},\n'contraindications': {contraindications}\n")
            
#             list_response = []
#             for channel_id in self.channel_ids:
#                 response = await retriever_product_hybrid_async(
#                     channel_id=channel_id,
#                     query=query,
#                     indications=indications,
#                     contraindications=contraindications,
#                     body_parts=body_parts,
#                 )
#                 logger.info(f"Ответ от 'product_search(channel_id:{channel_id})':\n{response}\n")
#                 logger.info(f"Количество 'product_search(channel_id:{channel_id})':{len(response)}\n")
#                 self._add_unique_by_product_name(list_response, response)
#             logger.info(f"ИТОГО количество 'product_search(channel_ids:{self.channel_ids})':{len(list_response)}\n")

#             return list_response 

#         return product_search

#     def get_tool(self) -> FastMCP:
#         """Возвращаем сам FastMCP инструмент для монтирования."""
#         print(f"self.channel_id: {self.channel_ids}")
#         return self.tool_product_search

#     def get_description(self) -> str:
#         """Возвращаем сам FastMCP инструмент для монтирования."""
#         return self.description


# if __name__=="__main__":
#     mcp = MCPSearchProductFull(channel_id='5')
#     print(mcp.get_description())


# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.tools.class_product_search_full