"""MCP-сервер записи клиента на выбранную услугу на дату и время."""

from typing import Any

from fastmcp import FastMCP

from ..crm.crm_record_time import record_time_async  # type: ignore
from ..postgres.postgres_util import read_secondary_article_by_primary  # type: ignore


tool_record_time = FastMCP(name="record_time")


@tool_record_time.tool(
    name="record_time",
    description=(
        "Запись клиента на медицинскую услугу в выбранную дату и время.\n\n"
        "**Назначение:**\n"
        "Используется, когда клиент подтвердил желание записаться на конкретную услугу "
        "в указанное время. Фиксирует запись для последующего подтверждения или обработки.\n\n"
        "**Args:**\n"
        "- session_id (`str`, required): ID dialog session.\n"
        "- office_id (`str`, required): ID филиала.\n"
        "- date (`str`, required): Дата записи в формате YYYY-MM-DD (пример: 2025-07-22).\n"
        "- time (`str`, required): Время записи в формате HH:MM (пример: 08:00, 13:00).\n"
        "- product_id (`str`, required): Идентификатор услуги (формат: 1-232324).\n"
        "- client_id (`int`, required): ID клиента.\n"
        "- master_id (`int`, optional): ID мастера.\n\n"
        "**Returns:**\n"
        "- `dict`: Результат записи (success=True при успехе).\n"
    ),
)
async def record_time(
    session_id: str,
    office_id: str,
    date: str,
    time: str,
    product_id: str,
    client_id: int,
    master_id: int = 0,
) -> dict[str, Any]:
    """Записать клиента на услугу на указанную дату и время."""
    _ = session_id  # session_id используется в описании tool-а; тут не нужен

    primary_channel_str = product_id.split("-", 1)[0]

    try:
        office_id_int = int(office_id)
    except ValueError as exc:
        raise ValueError(
            f"Некорректный office_id: {office_id!r}. Ожидалось число, например '19'."
        ) from exc

    try:
        primary_channel_int = int(primary_channel_str)
    except ValueError as exc:
        raise ValueError(
            "Некорректный primary_channel в product_id: "
            f"{product_id!r}. Ожидался формат 'число-число', например '1-232324'."
        ) from exc

    if office_id_int != primary_channel_int:
        secondary_product_id = await read_secondary_article_by_primary(
            primary_article=product_id,
            primary_channel=primary_channel_int,
            secondary_channel=office_id_int,
        )
        if secondary_product_id is None:
            raise RuntimeError(
                "Не найден secondary article для услуги. "
                f"primary={product_id!r} primary_channel={primary_channel_int!r} office_id={office_id_int!r}"
            )
        product_id = secondary_product_id

    return await record_time_async(
        date=date,
        time=time,
        product_id=product_id,
        user_id=client_id,
        staff_id=master_id,
    )

