"""server_spec_factory.py — централизованная сборка FastMCP по ServerSpec.

Здесь единственное место, где применяется tools_namespace из реестра.
"""

from __future__ import annotations

from fastmcp import FastMCP

from .server_common import build_mcp, get_env_csv
from .server_types import ServerSpec


async def build_mcp_from_spec(spec: ServerSpec) -> FastMCP:
    """Собирает FastMCP для указанного ServerSpec."""
    channel_ids = get_env_csv(spec.channel_ids_env)
    tools = await spec.build_tools(spec.name, channel_ids)

    mounts = [(tool, spec.tools_namespace) for tool in tools]
    return build_mcp(name=spec.name, mounts=mounts)
