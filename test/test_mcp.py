import asyncio
import pytest

from fastmcp import FastMCP
from src.tools.faq import tool_faq

import pytest_asyncio

@pytest_asyncio.fixture
async def mcp_server():
    mcp = FastMCP(name="Alisa")
    mcp.mount(tool_faq, 'zena')

    server_task = asyncio.create_task(
        mcp.run_async(transport="sse", port=4010, host="127.0.0.1")
    )
    await asyncio.sleep(10)
    yield
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_mcp_server_client(mcp_server):
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    url = 'http://127.0.0.1:4010/sse/'

    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                'zena_faq',
                {
                    'query': 'Как заморозить абонемент?',
                    'channel_id': 2
                }
            )
            assert hasattr(result, 'content')
            assert isinstance(result.content, list) or isinstance(result.content, str)
