import logging
import asyncio
import importlib

from src.runtime import init_runtime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def test_crm_get_client_records():
    mod = importlib.import_module("src.crm.crm_get_client_records")
    result = await mod.get_client_records(
        user_companychat=145,
        channel_id=1,  # или "telegram" — как у вас принято
    )
    logger.info(f"\n\nRESULT src.crm.crm_get_client_records:\n{result}")



async def main():
    init_runtime()
    await test_crm_get_client_records()


if __name__ == "__main__":
    asyncio.run(main())

# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.crm._crm_test