"""
main_v2.py — главный вход в mcpserver (FAIL-FAST supervisor).

Запускает несколько MCP-tenant'ов в одном процессе и:
- падает, если падает ЛЮБОЙ tenant
- корректно обрабатывает SIGINT / SIGTERM
- закрывает Postgres / HTTP клиенты

ENV (dev/prod) загружается через init_runtime().
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
from typing import Awaitable, Callable

from fastmcp import FastMCP

# --------------------------------------------------------------------------
# РЕСУРСЫ
# --------------------------------------------------------------------------
from src.postgres.db_pool import init_pg_pool, close_pg_pool
from src.clients import init_clients, close_clients
from src.runtime import init_runtime
from src.settings import get_settings

# --------------------------------------------------------------------------
# ЛОГИРОВАНИЕ
# --------------------------------------------------------------------------
logger = logging.getLogger("mcpserver")


def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


# --------------------------------------------------------------------------
# ENV HELPERS
# --------------------------------------------------------------------------
def require_int_env(name: str) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        raise RuntimeError(f"Отсутствует env переменная: {name}")
    try:
        return int(raw)
    except ValueError as e:
        raise RuntimeError(f"Некорректный int в env {name}={raw!r}") from e


def require_nonempty_env(name: str) -> str:
    """
    Читает env и гарантирует, что значение непустое.

    Используется для CHANNEL_IDS_* (fail-fast).
    """
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        raise RuntimeError(f"Отсутствует или пустая env переменная: {name}")
    return raw


# --------------------------------------------------------------------------
# MCP RUNNER
# --------------------------------------------------------------------------
BuildFn = Callable[[], Awaitable[FastMCP]]


async def run_one(name: str, port: int, build: BuildFn) -> None:
    logger.info("mcp.start tenant=%s port=%s", name, port)

    try:
        mcp = await build()
    except asyncio.CancelledError:
        logger.info("mcp.build.cancelled tenant=%s", name)
        raise
    except Exception:
        logger.exception("mcp.build.failed tenant=%s", name)
        raise
    else:
        logger.info("mcp.build.ok tenant=%s", name)

    try:
        await mcp.run_async(
            transport="sse",
            host="0.0.0.0",
            port=port,
        )
    except asyncio.CancelledError:
        logger.info("mcp.run.cancelled tenant=%s", name)
        raise
    except OSError:
        logger.exception("mcp.run.oserror tenant=%s port=%s", name, port)
        raise
    except Exception:
        logger.exception("mcp.run.failed tenant=%s", name)
        raise
    finally:
        logger.info("mcp.run.exit tenant=%s", name)


# --------------------------------------------------------------------------
# POSTGRES CHECK
# --------------------------------------------------------------------------
async def check_postgres_is_alive() -> None:
    pg_timeout = float(os.getenv("PG_QUERY_TIMEOUT_S", "5"))
    from src.postgres.db_pool import get_pg_pool

    pool = get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("SELECT 1", timeout=pg_timeout)


# --------------------------------------------------------------------------
# SUPERVISOR HELPERS
# --------------------------------------------------------------------------
async def cancel_and_await(tasks: list[asyncio.Task[None]]) -> None:
    """
    Единый путь "мягкой" остановки: cancel всем + await gather.
    """
    for t in tasks:
        if not t.done():
            t.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def start_tenants(SERVERS) -> list[asyncio.Task[None]]:
    """
    Стартует tenant-задачи (serve) и возвращает список asyncio.Task.
    Включает fail-fast валидацию env на tenant.
    """
    tasks: list[asyncio.Task[None]] = []

    for spec in SERVERS:
        port = require_int_env(spec.env_port)

        # FAIL-FAST: channel_ids должны быть заданы
        require_nonempty_env(spec.channel_ids_env)

        build = spec.build
        if build is None:
            raise RuntimeError(f"spec.build is not set for tenant={spec.name}")

        task = asyncio.create_task(
            run_one(spec.name, port, build),
            name=f"mcp:{spec.name}",
        )
        tasks.append(task)

    logger.info("tenants started: %s", [(t.get_name()) for t in tasks])
    return tasks


async def wait_stop_or_failure(
    tasks: list[asyncio.Task[None]],
    stop_event: asyncio.Event,
) -> None:
    """
    Семантика supervisor-а:
      - stop_event -> graceful shutdown (return)
      - завершение любого tenant-task:
          - с исключением -> fail-fast (raise исключение)
          - без исключения -> тоже fail-fast (serve() не должен завершаться сам)
    """
    stop_task = asyncio.create_task(stop_event.wait(), name="stop_event")
    try:
        done, _pending = await asyncio.wait(
            [*tasks, stop_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # GRACEFUL SHUTDOWN
        if stop_task in done:
            logger.info("graceful shutdown requested")
            return

        # FAIL-FAST: завершился tenant
        logger.error("one of MCP servers exited — FAIL-FAST")
        for t in done:
            if t is stop_task:
                continue

            exc = t.exception()
            if exc is not None:
                logger.error(
                    "server crashed",
                    extra={"task": t.get_name(), "error": repr(exc)},
                    exc_info=exc,
                )
                raise exc

            logger.error("server exited unexpectedly", extra={"task": t.get_name()})
            raise RuntimeError(f"server exited unexpectedly: {t.get_name()}")

    finally:
        stop_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stop_task


# --------------------------------------------------------------------------
# SUPERVISOR
# --------------------------------------------------------------------------
async def main() -> None:
    pg_inited = False
    http_inited = False

    # --------------------------------------------------
    # ENV + LOGGING
    # --------------------------------------------------
    init_runtime()
    setup_logging()

    from src.server.server_registry import SERVERS

    settings = get_settings()
    logger.info("Runtime ENV=%s LOG_LEVEL=%s", settings.ENV, settings.LOG_LEVEL)

    loop = asyncio.get_running_loop()

    # --------------------------------------------------
    # POSTGRES
    # --------------------------------------------------
    logger.info("initializing postgres pool")
    await init_pg_pool()
    pg_inited = True

    try:
        await check_postgres_is_alive()
    except Exception:
        logger.exception("postgres is not responding")
        raise

    # --------------------------------------------------
    # HTTP CLIENTS
    # --------------------------------------------------
    logger.info("initializing http clients")
    await init_clients()
    http_inited = True

    # --------------------------------------------------
    # SHUTDOWN SIGNAL
    # --------------------------------------------------
    stop_event = asyncio.Event()

    def _request_stop() -> None:
        logger.info("shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            pass

    tasks: list[asyncio.Task[None]] = []

    try:
        # --------------------------------------------------
        # START TENANTS
        # --------------------------------------------------
        tasks = await start_tenants(SERVERS)

        # --------------------------------------------------
        # WAIT (stop OR fail-fast)
        # --------------------------------------------------
        await wait_stop_or_failure(tasks, stop_event)
        return

    finally:
        # --------------------------------------------------
        # CLEANUP
        # --------------------------------------------------

        # Сначала гарантированно гасим tenant-задачи,
        # чтобы они не работали в момент закрытия пула/клиентов.
        await cancel_and_await(tasks)

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.remove_signal_handler(sig)
            except NotImplementedError:
                pass

        if http_inited:
            logger.info("closing http clients")
            await close_clients()

        if pg_inited:
            logger.info("closing postgres pool")
            await close_pg_pool()


# --------------------------------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())




# """
# main_v2.py — главный вход в mcpserver (FAIL-FAST supervisor).

# Запускает несколько MCP-tenant'ов в одном процессе и:
# - падает, если падает ЛЮБОЙ tenant
# - корректно обрабатывает SIGINT / SIGTERM
# - закрывает Postgres / HTTP клиенты

# ENV (dev/prod) загружается через init_runtime().
# """

# from __future__ import annotations

# import asyncio
# import logging
# import os
# import signal
# import traceback
# from typing import Awaitable, Callable

# from fastmcp import FastMCP

# # --------------------------------------------------------------------------
# # РЕСУРСЫ
# # --------------------------------------------------------------------------
# from src.postgres.db_pool import init_pg_pool, close_pg_pool
# from src.clients import init_clients, close_clients
# from src.runtime import init_runtime
# from src.settings import get_settings


# # --------------------------------------------------------------------------
# # ЛОГИРОВАНИЕ
# # --------------------------------------------------------------------------
# logger = logging.getLogger("mcpserver")


# def setup_logging() -> None:
#     level = os.getenv("LOG_LEVEL", "INFO").upper()
#     logging.basicConfig(
#         level=level,
#         format="%(asctime)s %(levelname)s %(name)s %(message)s",
#     )


# # --------------------------------------------------------------------------
# # ENV HELPERS
# # --------------------------------------------------------------------------
# def require_int_env(name: str) -> int:
#     raw = os.getenv(name)
#     if raw is None or raw.strip() == "":
#         raise RuntimeError(f"Отсутствует env переменная: {name}")
#     try:
#         return int(raw)
#     except ValueError as e:
#         raise RuntimeError(f"Некорректный int в env {name}={raw!r}") from e


# def require_nonempty_env(name: str) -> str:
#     """
#     Читает env и гарантирует, что значение непустое.

#     Используется для CHANNEL_IDS_* (fail-fast).
#     """
#     raw = os.getenv(name)
#     if raw is None or raw.strip() == "":
#         raise RuntimeError(f"Отсутствует или пустая env переменная: {name}")
#     return raw


# # --------------------------------------------------------------------------
# # MCP RUNNER
# # --------------------------------------------------------------------------
# BuildFn = Callable[[], Awaitable[FastMCP]]


# async def run_one(name: str, port: int, build: BuildFn) -> None:
#     logger.info("mcp.start tenant=%s port=%s", name, port)

#     try:
#         mcp = await build()
#     except asyncio.CancelledError:
#         logger.info("mcp.build.cancelled tenant=%s", name)
#         raise
#     except Exception:
#         logger.exception("mcp.build.failed tenant=%s", name)
#         raise
#     else:
#         logger.info("mcp.build.ok tenant=%s", name)

#     try:
#         await mcp.run_async(
#             transport="sse",
#             host="0.0.0.0",
#             port=port,
#         )
#     except asyncio.CancelledError:
#         logger.info("mcp.run.cancelled tenant=%s", name)
#         raise
#     except OSError:
#         logger.exception("mcp.run.oserror tenant=%s port=%s", name, port)
#         raise
#     except Exception:
#         logger.exception("mcp.run.failed tenant=%s", name)
#         raise
#     finally:
#         logger.info("mcp.run.exit tenant=%s", name)


# # --------------------------------------------------------------------------
# # POSTGRES CHECK
# # --------------------------------------------------------------------------
# async def check_postgres_is_alive() -> None:
#     pg_timeout = float(os.getenv("PG_QUERY_TIMEOUT_S", "5"))
#     from src.postgres.db_pool import get_pg_pool

#     pool = get_pg_pool()
#     async with pool.acquire() as conn:
#         await conn.execute("SELECT 1", timeout=pg_timeout)


# # --------------------------------------------------------------------------
# # SUPERVISOR
# # --------------------------------------------------------------------------
# async def main() -> None:
#     pg_inited = False
#     http_inited = False

#     # --------------------------------------------------
#     # ENV + LOGGING
#     # --------------------------------------------------
#     init_runtime()
#     setup_logging()

#     from src.server.server_registry import SERVERS

#     settings = get_settings()
#     logger.info("Runtime ENV=%s LOG_LEVEL=%s", settings.ENV, settings.LOG_LEVEL)

#     loop = asyncio.get_running_loop()

#     # --------------------------------------------------
#     # POSTGRES
#     # --------------------------------------------------
#     logger.info("initializing postgres pool")
#     await init_pg_pool()
#     pg_inited = True

#     try:
#         await check_postgres_is_alive()
#     except Exception as e:
#         logger.error("postgres is not responding", extra={"error": repr(e)})
#         raise

#     # --------------------------------------------------
#     # HTTP CLIENTS
#     # --------------------------------------------------
#     logger.info("initializing http clients")
#     await init_clients()
#     http_inited = True

#     # --------------------------------------------------
#     # SHUTDOWN SIGNAL
#     # --------------------------------------------------
#     stop_event = asyncio.Event()

#     def _request_stop() -> None:
#         logger.info("shutdown signal received")
#         stop_event.set()

#     for sig in (signal.SIGINT, signal.SIGTERM):
#         try:
#             loop.add_signal_handler(sig, _request_stop)
#         except NotImplementedError:
#             pass

#     tasks: list[asyncio.Task[None]] = []
#     stop_task: asyncio.Task | None = None

#     try:
#         # --------------------------------------------------
#         # START TENANTS
#         # --------------------------------------------------
#         for spec in SERVERS:
#             port = require_int_env(spec.env_port)

#             # FAIL-FAST: channel_ids должны быть заданы
#             require_nonempty_env(spec.channel_ids_env)

#             build = spec.build
#             if build is None:
#                 raise RuntimeError(f"spec.build is not set for tenant={spec.name}")

#             task = asyncio.create_task(
#                 run_one(spec.name, port, build),
#                 name=f"mcp:{spec.name}",
#             )
#             tasks.append(task)

#         # FIX: создаём stop_task (раньше он всегда был None)
#         stop_task = asyncio.create_task(stop_event.wait(), name="stop_event")

#         # --------------------------------------------------
#         # WAIT
#         # --------------------------------------------------
#         done, pending = await asyncio.wait(
#             [*tasks, stop_task],
#             return_when=asyncio.FIRST_COMPLETED,
#         )

#         # GRACEFUL SHUTDOWN
#         if stop_task in done:
#             logger.info("graceful shutdown requested")
#             for t in tasks:
#                 t.cancel()
#             await asyncio.gather(*tasks, return_exceptions=True)
#             return

#         # FAIL-FAST
#         logger.error("one of MCP servers crashed — FAIL-FAST")

#         for t in done:
#             if t is stop_task:
#                 continue
#             exc = t.exception()
#             if exc:
#                 logger.error("server crashed", extra={"task": t.get_name(), "error": repr(exc)})
#                 traceback.print_exception(type(exc), exc, exc.__traceback__)
#             else:
#                 logger.error("server exited unexpectedly", extra={"task": t.get_name()})

#         for t in pending:
#             t.cancel()

#         await asyncio.gather(*pending, return_exceptions=True)
#         raise SystemExit(1)

#     finally:
#         # --------------------------------------------------
#         # CLEANUP
#         # --------------------------------------------------

#         # FIX: сначала гарантированно гасим tenant-задачи,
#         # чтобы они не работали в момент закрытия пула/клиентов.
#         for t in tasks:
#             if not t.done():
#                 t.cancel()
#         if tasks:
#             await asyncio.gather(*tasks, return_exceptions=True)

#         if stop_task is not None and not stop_task.done():
#             stop_task.cancel()
#             await asyncio.gather(stop_task, return_exceptions=True)

#         for sig in (signal.SIGINT, signal.SIGTERM):
#             try:
#                 loop.remove_signal_handler(sig)
#             except NotImplementedError:
#                 pass

#         if http_inited:
#             logger.info("closing http clients")
#             await close_clients()

#         if pg_inited:
#             logger.info("closing postgres pool")
#             await close_pg_pool()


# # --------------------------------------------------------------------------
# # ENTRYPOINT
# # --------------------------------------------------------------------------
# if __name__ == "__main__":
#     asyncio.run(main())



# """
# main_v2.py — главный вход в mcpserver (вариант A: FAIL-FAST)

# Этот файл — СУПЕРВИЗОР.

# Он отвечает за:
# - запуск нескольких MCP-серверов (tenants) в одном процессе
# - контроль их состояния
# - корректную остановку по сигналам (SIGTERM / Ctrl+C)
# - fail-fast поведение:
#     если ЛЮБОЙ сервер падает → останавливаем ВСЁ и завершаем процесс

# Почему так:
# - Docker / Kubernetes увидят, что процесс умер
# - и автоматически перезапустят контейнер

# Версия ниже — "вставляй и запускай":
# - аккуратные импорты (важно для env и типов)
# - корректный вывод traceback
# - безопасная финальная уборка (не падаем в finally, если init не успел)
# - подробные комментарии для новичка
# """

# from __future__ import annotations

# import asyncio
# import logging
# import os
# import signal
# import traceback
# from typing import TYPE_CHECKING, Awaitable, Callable

# from fastmcp import FastMCP

# # --------------------------------------------------------------------------
# # ИМПОРТЫ РЕСУРСОВ (Postgres / HTTP клиенты)
# # --------------------------------------------------------------------------
# # Важно:
# # - init_pg_pool() должен вызываться РОВНО 1 раз при старте процесса
# # - close_pg_pool() должен вызываться РОВНО 1 раз при остановке процесса
# from src.postgres.db_pool import init_pg_pool, close_pg_pool
# from src.clients import init_clients, close_clients

# # init_runtime() — единая функция загрузки env (вне Docker)
# # Обычно она читает dev.env/prod.env и переносит значения в os.environ
# from src.runtime import init_runtime

# # get_settings() — функция, которая читает переменные окружения (os.environ)
# # и возвращает объект настроек (обычно pydantic BaseSettings).
# # Внутри у неё, как правило, есть кеширование (lru_cache),
# # чтобы настройки читались 1 раз.
# from src.settings import get_settings

# # Для type hints: BuildFn мы импортируем только в TYPE_CHECKING,
# # чтобы не тянуть реестр серверов ДО init_runtime().
# # Это важно, потому что реестр часто тянет "бизнес-код", который может
# # читать env при импорте (и тогда всё сломается).
# if TYPE_CHECKING:
#     from src.server.server_registry import BuildFn


# # --------------------------------------------------------------------------
# # ЛОГИРОВАНИЕ
# # --------------------------------------------------------------------------
# # Создаём логгер с фиксированным именем.
# # Его удобно фильтровать в логах и использовать во всём файле.
# logger = logging.getLogger("mcpserver")

# def setup_logging() -> None:
#     """
#     Настройка логирования.

#     Что здесь происходит:
#     - берём уровень логов из переменной окружения LOG_LEVEL
#       (DEBUG / INFO / WARNING / ERROR)
#     - если переменной нет — используем INFO
#     - выводим логи в stdout (важно для Docker)

#     Почему используем os.getenv(), а не settings?
#     - Потому что логирование надо настроить как можно раньше.
#     - Но init_runtime() уже выполняется до вызова setup_logging(),
#       значит env уже "в боевом виде".
#     """
#     level = os.getenv("LOG_LEVEL", "INFO").upper()

#     logging.basicConfig(
#         level=level,
#         format="%(asctime)s %(levelname)s %(name)s %(message)s",
#     )


# # --------------------------------------------------------------------------
# # ВСПОМОГАТЕЛЬНОЕ: чтение int из env (fail-fast)
# # --------------------------------------------------------------------------
# def require_int_env(name: str) -> int:
#     """
#     Читает переменную окружения и ГАРАНТИРУЕТ, что это int.

#     Fail-fast подход:
#     - если переменной нет → падаем сразу
#     - если значение не число → падаем сразу

#     Почему это полезно:
#     - лучше упасть при старте, чем словить странный баг позже
#     - Docker/K8s увидят, что процесс умер, и перезапустят контейнер
#     """
#     raw = os.getenv(name)
#     if raw is None or raw.strip() == "":
#         raise RuntimeError(f"Отсутствует необходимая переменная окружения: {name}")

#     try:
#         return int(raw)
#     except ValueError as e:
#         raise RuntimeError(f"Недопустимое значение int в env var {name}={raw!r}") from e


# # --------------------------------------------------------------------------
# # ЗАПУСК ОДНОГО MCP-СЕРВЕРА
# # --------------------------------------------------------------------------
# BuildFn = Callable[[], Awaitable[FastMCP]]

# async def run_one(name: str, port: int, build: BuildFn) -> None:
#     logger.info("mcp.start tenant=%s port=%s", name, port)

#     # 1) BUILD phase
#     try:
#         mcp = await build()
#     except asyncio.CancelledError:
#         logger.info("mcp.build.cancelled tenant=%s port=%s", name, port)
#         raise
#     except Exception:
#         # Ключевое: отличаем "упали на сборке" от "упали на рантайме"
#         logger.exception("mcp.build.failed tenant=%s port=%s", name, port)
#         raise
#     else:
#         logger.info("mcp.build.ok tenant=%s port=%s", name, port)

#     # 2) RUN phase
#     try:
#         await mcp.run_async(
#             transport="sse",
#             host="0.0.0.0",
#             port=port,
#         )
#     except asyncio.CancelledError:
#         logger.info("mcp.run.cancelled tenant=%s port=%s", name, port)
#         raise
#     except OSError:
#         # Частый кейс: порт занят / нет прав / network bind error
#         logger.exception("mcp.run.oserror tenant=%s port=%s", name, port)
#         raise
#     except Exception:
#         logger.exception("mcp.run.failed tenant=%s port=%s", name, port)
#         raise
#     finally:
#         logger.info("mcp.run.exit tenant=%s port=%s", name, port)



# # --------------------------------------------------------------------------
# # (ОПЦИОНАЛЬНО) ПРОВЕРКА, ЧТО POSTGRES ЖИВОЙ
# # --------------------------------------------------------------------------
# async def check_postgres_is_alive() -> None:
#     """
#     Простая проверка, что Postgres реально отвечает.

#     Зачем:
#     - init_pg_pool() создаёт пул
#     - но иногда хочется сразу проверить, что соединение устанавливается и запрос выполняется
#     - если БД "мертва" — лучше упасть при старте (fail-fast)

#     Как устроено:
#     - берём pool через get_pg_pool() (локальный импорт снижает связанность)
#     - делаем "SELECT 1" с небольшим таймаутом
#     """
#     pg_timeout = float(os.getenv("PG_QUERY_TIMEOUT_S", "5"))

#     from src.postgres.db_pool import get_pg_pool  # локальный импорт — меньше связности

#     pool = get_pg_pool()
#     async with pool.acquire() as conn:
#         await conn.execute("SELECT 1", timeout=pg_timeout)


# # --------------------------------------------------------------------------
# # ГЛАВНАЯ ФУНКЦИЯ-СУПЕРВИЗОР
# # --------------------------------------------------------------------------
# async def main() -> None:
#     """
#     Главная функция-супервизор (FAIL-FAST).

#     Алгоритм:
#     1) загрузить env + настроить логирование
#     2) инициализировать Postgres pool (fail-fast)
#     3) запустить MCP-сервера как asyncio задачи
#     4) ждать:
#         - либо SIGTERM / Ctrl+C
#         - либо падение любого сервера
#     5) корректно всё остановить (и Postgres pool тоже)
#     """

#     # Флаги, чтобы в finally не пытаться закрыть то,
#     # что не успели открыть (это снижает шанс "вторичной" ошибки).
#     pg_inited = False
#     http_inited = False

#     # ----------------------------------------------------------------------
#     # ШАГ 0. ENV + LOGGING
#     # ----------------------------------------------------------------------
#     # init_runtime() должен быть первым:
#     # он загружает env из файла (например dev.env) в os.environ.
#     init_runtime()

#     # После init_runtime() можно безопасно настраивать логирование.
#     setup_logging()

#     # Импортируем реестр tenants ТОЛЬКО после init_runtime().
#     # Это важно: реестр может тянуть "бизнес-код" и settings при импорте.
#     from src.server.server_registry import SERVERS  # noqa: WPS433

#     # Читаем settings (кешируется внутри get_settings()).
#     settings = get_settings()
#     logger.info("Runtime ENV=%s LOG_LEVEL=%s", settings.ENV, settings.LOG_LEVEL)

#     # Текущий event loop (нужен для add_signal_handler/remove_signal_handler)
#     loop = asyncio.get_running_loop()

#     # ----------------------------------------------------------------------
#     # ШАГ 1. POSTGRES POOL (FAIL-FAST)
#     # ----------------------------------------------------------------------
#     logger.info("initializing postgres pool")
#     await init_pg_pool()
#     pg_inited = True

#     # Проверяем, что БД реально отвечает.
#     # Если тут упадём — это правильно: сервис не должен стартовать "полумёртвым".
#     try:
#         await check_postgres_is_alive()
#     except Exception as e:
#         logger.error("postgres is not responding on startup", extra={"error": repr(e)})
#         raise

#     # ----------------------------------------------------------------------
#     # ШАГ 1.2. HTTP CLIENTS
#     # ----------------------------------------------------------------------
#     logger.info("initializing http clients")
#     await init_clients()
#     http_inited = True

#     # ----------------------------------------------------------------------
#     # ШАГ 2. STOP-EVENT ДЛЯ GRACEFUL SHUTDOWN
#     # ----------------------------------------------------------------------
#     stop_event = asyncio.Event()

#     def _request_stop() -> None:
#         """
#         Вызывается при SIGINT / SIGTERM.

#         ВАЖНО:
#         - обработчик сигнала должен быть коротким
#         - мы ТОЛЬКО ставим флаг
#         """
#         logger.info("shutdown signal received")
#         stop_event.set()

#     # Регистрируем обработчики сигналов.
#     # SIGINT  = Ctrl+C
#     # SIGTERM = docker stop / k8s termination
#     for sig in (signal.SIGINT, signal.SIGTERM):
#         try:
#             loop.add_signal_handler(sig, _request_stop)
#         except NotImplementedError:
#             # Некоторые окружения (например Windows) не поддерживают add_signal_handler
#             pass

#     tasks: list[asyncio.Task[None]] = []
#     stop_task: asyncio.Task[bool] | None = None

#     try:
#         # ------------------------------------------------------------------
#         # ШАГ 3. ЗАПУСК MCP-СЕРВЕРОВ
#         # ------------------------------------------------------------------
#         for spec in SERVERS:
#             # Читаем порт из env (fail-fast)
#             port = require_int_env(spec.env_port)

#             # Создаём asyncio-задачу на каждый tenant
#             task = asyncio.create_task(
#                 run_one(spec.name, port, spec.build),
#                 name=f"mcp:{spec.name}",
#             )
#             tasks.append(task)

#         logger.info(
#             "all MCP server tasks scheduled",
#             extra={"tenants": [s.name for s in SERVERS]},
#         )

#         # Задача, которая завершится при stop_event
#         stop_task = asyncio.create_task(stop_event.wait(), name="stop_event")

#         # ------------------------------------------------------------------
#         # ШАГ 4. ЖДЁМ ПЕРВОЕ СОБЫТИЕ:
#         # - либо stop_event (сигнал остановки)
#         # - либо падение одного из MCP серверов
#         # ------------------------------------------------------------------
#         done, pending = await asyncio.wait(
#             [*tasks, stop_task],
#             return_when=asyncio.FIRST_COMPLETED,
#         )

#         # ------------------------------------------------------------------
#         # ВЕТКА A: GRACEFUL SHUTDOWN
#         # ------------------------------------------------------------------
#         if any(t.get_name() == "stop_event" for t in done):
#             logger.info("stopping all MCP servers")

#             # Просим все сервера остановиться
#             for t in tasks:
#                 t.cancel()

#             # Ждём, пока они реально завершатся
#             await asyncio.gather(*tasks, return_exceptions=True)

#             logger.info("shutdown complete")
#             return

#         # ------------------------------------------------------------------
#         # ВЕТКА B: FAIL-FAST
#         # ------------------------------------------------------------------
#         logger.error("one of MCP servers crashed — FAIL-FAST")

#         # Логируем, кто именно упал
#         for t in done:
#             if t.get_name() == "stop_event":
#                 continue

#             exc = t.exception()
#             if exc:
#                 # Корректный вывод traceback для Exception
#                 logger.error("server crashed", extra={"task": t.get_name(), "error": repr(exc)})
#                 traceback.print_exception(type(exc), exc, exc.__traceback__)
#             else:
#                 logger.error("server exited unexpectedly", extra={"task": t.get_name()})

#         # Останавливаем всех остальных (и stop_task тоже может быть pending)
#         for t in pending:
#             t.cancel()

#         await asyncio.gather(*pending, return_exceptions=True)

#         # Выходим с кодом ошибки → Docker/K8s перезапустят
#         raise SystemExit(1)

#     finally:
#         # ------------------------------------------------------------------
#         # ШАГ 5. ФИНАЛЬНАЯ УБОРКА
#         # ------------------------------------------------------------------

#         # 5.1 Убираем обработчики сигналов (не обязательно, но аккуратно)
#         for sig in (signal.SIGINT, signal.SIGTERM):
#             try:
#                 loop.remove_signal_handler(sig)
#             except NotImplementedError:
#                 pass

#         # 5.2 Останавливаем stop_task, если она ещё жива
#         if stop_task is not None and not stop_task.done():
#             stop_task.cancel()
#             await asyncio.gather(stop_task, return_exceptions=True)

#         # 5.3 Закрываем HTTP клиентов (если успели открыть)
#         if http_inited:
#             logger.info("closing http clients")
#             await close_clients()

#         # 5.4 Закрываем Postgres pool (если успели открыть)
#         if pg_inited:
#             logger.info("closing postgres pool")
#             await close_pg_pool()


# # --------------------------------------------------------------------------
# # ТОЧКА ВХОДА
# # --------------------------------------------------------------------------
# if __name__ == "__main__":
#     # asyncio.run создаёт event loop, запускает main, а потом закрывает loop.
#     # Если внутри main случится SystemExit(1), процесс завершится с кодом 1.
#     asyncio.run(main())
