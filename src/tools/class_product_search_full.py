# class_product_search_full.py
"""Универсальный клас создания mcp-сервера поиска услуг.

Контракт ответа: только ok()/err() из _crm_result.py
- ok(list[dict]) — поиск выполнен, список может быть пустым
- err(code, error) — ошибка валидации/конфига/внутренняя ошибка
"""

from __future__ import annotations

import asyncio
import logging
import textwrap
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from src.crm._crm_result import Payload, err, ok

from ..postgres.postgres_util import select_key  # type: ignore
from ..qdrant.retriever_product import retriever_product_hybrid_async  # type: ignore


logger = logging.getLogger(__name__)


class MCPSearchProductFull:
    """Универсальный клас создания mcp-сервера поиска услуг."""

    # Чтобы не вредить tool-selection:
    # - держим описание коротким
    # - примеры добавляем в конце и строго ограничиваем размер
    _EXAMPLES_LIMIT_CHARS = 18000

    def __init__(self, channel_ids: list[str], key: dict[str, Any]) -> None:
        """
        Инициализация MCP-сервера полнотекстового поиска услуг.

        :param channel_ids: Список идентификаторов каналов,
            по которым выполняется поиск услуг.
        :param key: Словарь справочников (indications, contraindications,
            body_parts), полученный из конфигурационного хранилища.
        """
        self.channel_ids: list[str] = channel_ids
        self.key: dict[str, Any] = key

        self.description: str = self._set_description()
        self.tool_product_search: FastMCP = FastMCP(name="product_search")
        self._register_tool()

    @classmethod
    async def create(cls, channel_ids: list[str]) -> MCPSearchProductFull:
        """
        Фабричный метод создания MCP-сервера с загрузкой ключей из PostgreSQL.

        Выполняет:
        - валидацию channel_ids
        - получение сервисных ключей для первого channel_id
        - создание экземпляра MCPSearchProductFull

        :param channel_ids: Список идентификаторов каналов.
        :raises RuntimeError: Если channel_ids пуст,
            имеет некорректный формат или ключи не найдены.
        :return: Инициализированный экземпляр MCPSearchProductFull.
        """
        if not channel_ids:
            raise RuntimeError(
                "channel_ids пустой. Проверь переменную окружения CHANNEL_IDS_*"
            )

        try:
            channel_id = int(channel_ids[0])
        except (TypeError, ValueError):
            raise RuntimeError(f"Некорректный channel_id в env: {channel_ids[0]!r}")

        key = await select_key(channel_id=channel_id)
        if not key:
            raise RuntimeError(
                f"Нет сервисных ключей для channel_id={channel_id}. "
                "Проверьте view_channel_services_keys / env / channel_ids."
            )
        return cls(channel_ids=channel_ids, key=key)

    def _pretty_list_multiline(self, raw: Any, per_line: int = 10) -> str:
        if not raw:
            return "  - нет данных -"

        if isinstance(raw, str):
            items = [x.strip().strip('"') for x in raw.split(",")]
        elif isinstance(raw, list):
            items = [str(x).strip() for x in raw]
        else:
            return str(raw)

        items = [x for x in items if x]

        lines: list[str] = []
        for i in range(0, len(items), per_line):
            chunk = items[i : i + per_line]
            lines.append("  - " + ", ".join(chunk))

        return "\n".join(lines)

    def _examples_block(self) -> str:
        """
        Примеры держим.

        - короткими (10 -> 4–5, без воды)
        - в конце description
        - с <session_id> как плейсхолдером
        - ограничиваем общий размер, чтобы не давить tool-selection
        """
        examples = textwrap.dedent(
            """
            ────────────────────
            ПРИМЕРЫ ВЫЗОВА
            ────────────────────

            Пример 1: Клиент: «Мне нужен массаж, чтобы убрать отечность ног, но у меня варикоз»
            Вход:
            {
                "query": "массаж",
                "indications": ["отечность"],
                "contraindications": ["варикоз"],
                "body_parts": ["ноги"],
                "session_id": "1-232327692"
            }

            Пример 2: Клиент: «У меня редкие волосы на бровях, что можете предложить?»
            Вход:
            {
                "query": "",
                "indications": ["редкие"],
                "contraindications": [],
                "body_parts": ["брови", "волосы"],
                "session_id": "1-232327692"
            }

            Пример 3: Клиент: «Что у вас есть для лица?»
            Вход:
            {
                "query": "",
                "indications": [],
                "contraindications": [],
                "body_parts": ["лицо"],
                "session_id": "1-232327692"
            }

            Пример 4: Клиент: «Можно записаться на консультацию?»
            Вход:
            {
                "query": "консультация",
                "indications": [],
                "contraindications": [],
                "body_parts": [],
                "session_id": "1-232327692"
            }

            Пример 5: Клиент: «Есть ли услуги для коррекции фигуры?»
            Вход:
            {
                "query": "",
                "indications": ["коррекция фигуры"],
                "contraindications": [],
                "body_parts": [],
                "session_id": "1-232327692"
            }

            Пример 6: Клиент: «Нужна эпиляция волос в подмышках»
            Вход:
            {
                "query": "эпиляция",
                "indications": ["волосы"],
                "contraindications": [],
                "body_parts": ["подмышки"],
                "session_id": "1-232327692"
            }

            Пример 7: Клиент: «У вас есть акции на услуги?»
            Вход:
            {
                "query": "акции",
                "indications": [],
                "contraindications": [],
                "body_parts": [],
                "session_id": "1-232327692"
            }

            Пример 8: Клиент: «Какие есть комплексы для коррекции фигуры?»
            Вход:
            {
                "query": "комплексы",
                "indications": ["коррекция фигуры"],
                "contraindications": [],
                "body_parts": [],
                "session_id": "1-232327692"
            }

            Пример 9: Клиент: «какие есть процедуры для похудения»
            Вход:
            {
                "query": "",
                "indications": ["похудение"],
                "contraindications": [],
                "body_parts": [],
                "session_id": "1-232327692"
            }

            Пример 10: Клиент: «какие есть процедуры для уменьшения объемов тела»
            Вход:
            {
                "query": "",
                "indications": ["уменьшение объемов"],
                "contraindications": [],
                "body_parts": [тело],
                "session_id": "1-232327692"
            }            
            """
        ).strip()

        # safety limit
        if len(examples) > self._EXAMPLES_LIMIT_CHARS:
            examples = examples[: self._EXAMPLES_LIMIT_CHARS].rstrip() + "\n…"
        return examples

    def _set_description(self) -> str:
        # 1) "короткая" часть — важнее всего для модели
        header = textwrap.dedent(
            """
            Поиск услуг

            Инструмент подбирает услуги по:
            - query (свободный текст) И/ИЛИ
            - indications / contraindications / body_parts (строго из списков ниже)

            ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:
            - Используй ТОЛЬКО точные значения из списков ниже.
            - Не придумывай новые значения и не изменяй формулировки.
            - Если подходящих значений нет — верни пустой список [].
            - indications: максимум 2 значения.
            - contraindications: максимум 2 значения.
            - body_parts: максимум 2 значения.
            - session_id обязателен.
            - Если query пустой, заполни хотя бы один из списков (indications или body_parts), иначе оставь query непустым.
            - Если одно и то же значение подходит и для indications, и для contraindications — предпочитай indications.
            """
        ).strip()

        # 2) справочники — полезны, но тяжёлые; оставляем как есть
        params = textwrap.dedent(
            f"""
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
            РЕЗУЛЬТАТ (единый контракт)
            ────────────────────

            - ok(List[dict])  — список услуг (может быть пустым)
            - err(code,error) — ошибка валидации/конфига/внутренняя ошибка
            """
        ).strip()

        # 3) примеры — в самом конце и ограничены по длине
        return "\n\n".join([header, params, self._examples_block()]).strip()

    def _add_unique_by_product_name(
        self, target_list: list[dict[str, Any]], source_list: list[dict[str, Any]]
    ) -> None:
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
        ) -> Payload[list[dict[str, Any]]]:
            # Валидация
            if not session_id or not str(session_id).strip():
                return err(code="validation_error", error="session_id обязателен")

            # Мягкая защита от полностью пустого запроса:
            # если нет ни query, ни параметров — просто нечего искать.
            if (not query or not query.strip()) and not (
                indications or body_parts or contraindications
            ):
                return ok([])

            logger.info(
                "Запрос на 'product_search': channel_ids=%s session_id=%s query=%r body_parts=%r indications=%r contraindications=%r",
                self.channel_ids,
                session_id,
                query,
                body_parts,
                indications,
                contraindications,
            )

            list_response: list[dict[str, Any]] = []
            any_channel_completed = False

            for channel_id in self.channel_ids:
                try:
                    response = await retriever_product_hybrid_async(
                        channel_id=channel_id,
                        query=query,
                        indications=indications,
                        contraindications=contraindications,
                        body_parts=body_parts,
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
                    len(response),
                )
                if isinstance(response, list):
                    self._add_unique_by_product_name(list_response, response)

            logger.info(
                "[product_search] total_len=%s channel_ids=%s",
                len(list_response),
                self.channel_ids,
            )

            # Итог:
            # - если хотя бы один канал отработал (даже вернул []) — ok(...)
            # - если все каналы упали исключениями — err
            if any_channel_completed:
                return ok(list_response)

            return err(code="internal_error", error="Ошибка поиска услуг")

        return product_search

    def get_tool(self) -> FastMCP:
        """Возвращаем сам FastMCP инструмент для монтирования."""
        return self.tool_product_search

    def get_description(self) -> str:
        """Возврат описания инструмента."""
        return self.description
