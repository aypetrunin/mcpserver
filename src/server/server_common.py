import asyncio
import os

from typing import Iterable, Tuple, List, Callable, Mapping, Optional
from fastmcp import FastMCP
from pprint import pprint

from fastmcp import FastMCP


Mount = Tuple[object, str]  # (tool, namespace)


def build_mcp(name: str, mounts: Iterable[Mount]) -> FastMCP:
    mcp = FastMCP(name=name)
    for tool, namespace in mounts:
        mcp.mount(tool, namespace)
    return mcp


def require_env(name: str) -> str:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        raise RuntimeError(f"Отсутствует необходимая переменная окружения: {name}")
    return val


def get_env_int(name: str) -> int:
    raw = require_env(name)
    try:
        return int(raw)
    except ValueError as e:
        raise RuntimeError(f"Некорректный {name}={raw!r}: ожидается целое число") from e


def get_env_csv(name: str) -> List[str]:
    raw = require_env(name)
    return [item.strip() for item in raw.split(",") if item.strip()]


def debug_print_tools(mcp: FastMCP) -> None:
    tools = asyncio.run(mcp.get_tools())
    pprint([tool for tool in tools])

def run_standalone(
    *,
    build: Callable[[], FastMCP],
    port_env: str,
    defaults: Optional[Mapping[str, str]] = None,
    host: str = "0.0.0.0",
    transport: str = "sse",
    print_tools: bool = True,
) -> None:
    """
    Универсальный standalone-запуск для локальной проверки.
    - build: функция, которая собирает FastMCP (factory)
    - port_env: имя env-переменной с портом (например "MCP_PORT_VALENTINA")
    - defaults: env значения по умолчанию для локального запуска
    - print_tools: печатать ли список tools
    """
    if defaults:
        for k, v in defaults.items():
            os.environ.setdefault(k, v)

    mcp = build()

    if print_tools:
        debug_print_tools(mcp)

    port = get_env_int(port_env)
    # mcp.run(transport=transport, port=port, host=host)
