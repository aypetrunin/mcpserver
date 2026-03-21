"""Ручной тест CRM-методов через прямой импорт модулей."""

import asyncio
import importlib
import logging

from src.runtime import init_runtime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def test_crm_get_client_records() -> None:
    """Вызывает get_client_records и логирует результат."""
    mod = importlib.import_module("src.crm.crm_get_client_records")
    result = await mod.get_client_records(
        user_companychat=145,
        channel_id=19,
    )
    logger.info("\n\nRESULT src.crm.crm_get_client_records:\n%s", result)


async def test_crm_delete_client_record() -> None:
    """Вызывает delete_client_record и логирует результат."""
    mod = importlib.import_module("src.crm.crm_delete_client_record")
    result = await mod.delete_client_record(
        user_companychat=145,
        channel_id=19,
        record_id=1025370063,
    )
    logger.info("\n\nRESULT src.crm.crm_delete_client_record:\n%s", result)


async def main() -> None:
    """Запускает выбранный ручной тест."""
    init_runtime()
    # await test_crm_get_client_records()
    await test_crm_delete_client_record()


if __name__ == "__main__":
    asyncio.run(main())


# cd /home/copilot_superuser/petrunin/zena/mcpserver
# uv run python -m src.crm._crm_test
