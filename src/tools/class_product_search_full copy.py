# class_product_search_full.py

"""Универсальный клас создания mcp-сервера поиска услуг."""

from __future__ import annotations

import logging
import textwrap
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from ..postgres.postgres_util import select_key  # type: ignore
from ..qdrant.retriever_product import retriever_product_hybrid_async  # type: ignore


logger = logging.getLogger(__name__)

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
    async def create(cls, channel_ids: list[str]) -> MCPSearchProductFull:
        """Создаёт экземпляр MCPSearchProductFull с сервисным ключом.

        Определяет основной channel_id, получает соответствующий сервисный ключ
        и инициализирует объект. Если ключ для указанного канала не найден,
        возбуждает исключение RuntimeError.
        """
        channel_id = int(channel_ids[0])
        key = await select_key(channel_id=channel_id)
        if not key:
            raise RuntimeError(
                f"Нет сервисных ключей для channel_id={channel_id}. "
                "Проверьте view_channel_services_keys / env / channel_ids."
            )
        return cls(channel_ids=channel_ids, key=key)

    def _pretty_list_multiline(self, raw: Any, per_line: int = 10) -> str:
        """Форматирует список значений в многострочный вид.

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

Пример 9: Клиент: «какие есть процедуры для похудения»
Вход:
{{
    "query": "",
    "indications": ["похудение"],
    "contraindications": [],
    "body_parts": [],
    "session_id": "1-232327692"
}}

Пример 10: Клиент: «какие есть процедуры для уменьшения объемов тела»
Вход:
{{
    "query": "",
    "indications": ["уменьшение объемов"],
    "contraindications": [],
    "body_parts": [тело],
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
                "Запрос на 'product_search': channel_ids=%s session_id=%s query=%r body_parts=%r indications=%r contraindications=%r",
                self.channel_ids,
                session_id,
                query,
                body_parts,
                indications,
                contraindications,
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
                logger.info(
                    "[product_search] channel_id=%s response=%s",
                    channel_id,
                    response,
                )
                logger.info(
                    "[product_search] channel_id=%s response_len=%s",
                    channel_id,
                    len(response),
                )
                self._add_unique_by_product_name(list_response, response)

            logger.info(
                "[product_search] total_len=%s channel_ids=%s",
                len(list_response),
                self.channel_ids,
            )
            return list_response

        return product_search

    def get_tool(self) -> FastMCP:
        """Возвращаем сам FastMCP инструмент для монтирования."""
        return self.tool_product_search

    def get_description(self) -> str:
        """Возврат описания инструмента."""
        return self.description


if __name__ == "__main__":

    import asyncio

    from src.runtime import init_runtime

    from ..postgres.db_pool import init_pg_pool

    async def _main():
        init_runtime()
        await init_pg_pool()
        mcp = await MCPSearchProductFull.create(channel_ids=["1"])
        logger.info(mcp.get_description())

    asyncio.run(_main())
