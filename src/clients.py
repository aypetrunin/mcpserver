"""Назначение этого файла (объяснение для новичка).

Зачем вообще нужен "общий" (глобальный) HTTP-клиент?

В проекте много мест, где вы делаете HTTP-запросы (внешние API, ваши сервисы и т.п.).
Если каждый раз создавать новый httpx.AsyncClient прямо в функции, то:

1) Это медленнее:
   - создание клиента = создание пула соединений + настройка
   - при большом числе запросов это заметно "съедает" время и ресурсы.

2) Это хуже для сети:
   - повторно не используются keep-alive соединения
   - больше TCP/TLS рукопожатий → лишняя задержка.

3) Это сложнее закрывать:
   - легко забыть закрыть клиент (утечки сокетов)
   - или закрыть не там.

Поэтому мы делаем так же, как вы уже делаете с Postgres pool:
- инициализируем ресурс один раз при старте процесса
- используем его везде
- закрываем один раз при остановке процесса

Как этот модуль использовать:
1) На старте:
      await init_clients()

2) В любом месте проекта:
      client = get_http()
      resp = await client.post(...)

3) На shutdown:
      await close_clients()

Важная идея: клиент создаётся "на весь процесс" и переиспользуется.
"""

import logging

import httpx


logger = logging.getLogger(__name__)

_http: httpx.AsyncClient | None = None


async def init_clients() -> None:
    """Инициализирует общий HTTP-клиент."""
    global _http

    if _http is not None:
        logger.debug("HTTP client already initialized")
        return

    timeout = httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=3.0)
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=50)

    _http = httpx.AsyncClient(timeout=timeout, limits=limits)
    logger.info("HTTP client initialized")


def get_http() -> httpx.AsyncClient:
    """Возвращает общий HTTP-клиент."""
    if _http is None:
        logger.error("HTTP client requested before initialization")
        raise RuntimeError(
            "HTTP client is not initialized. "
            "Call init_clients() on startup (e.g. in main_v2.py)."
        )
    return _http


async def close_clients() -> None:
    """Закрывает общий HTTP-клиент."""
    global _http

    if _http is None:
        logger.debug("HTTP client already closed")
        return

    await _http.aclose()
    _http = None
    logger.info("HTTP client closed")
