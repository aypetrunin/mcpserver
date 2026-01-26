"""MCP-сервер записи клиента на выбранную услугу на определенную дату и время."""

from typing import Any

from fastmcp import FastMCP

from ..crm.crm_record_time import record_time_async  # type: ignore
from ..postgres.postgres_util import read_secondary_article_by_primary  # type: ignore


tool_record_time = FastMCP(name="record_time")


@tool_record_time.tool(
    name="record_time",
    description=(
        """
        Запись клиента на медицинскую услугу в выбранную дату и время.

        **Назначение:**
        Используется, когда клиент подтвердил желание записаться на конкретную услугу в указанное время.
        Фиксирует запись с именем и телефоном клиента для последующего подтверждения или обработки администрацией.

        **Args:**
        - session_id(str): id dialog session. **Обязательный параметр.**
        - office_id(str): id филиала. **Обязательный параметр.**
        - date (str): Дата записи в формате YYYY-MM-DD. Пример: '2025-07-22'. **Обязательный параметр.**
        - time (str): Время записи в формате HH:MM. Пример: '8:00', '13:00'. **Обязательный параметр.**
        - product_id (str): Идентификатор услуги. Формат: '1-232324'. **Обязательный параметр.**
        - client_id (int): ID клиента. **Обязательный параметр.**
        - master_id (int): ID мастера. **Не обязательный параметр.**

        **Returns:**
        - dict: success = True, если запись прошла успешно, иначе False.
        """
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
    """Функция записи на выбранную услугу на определенную дату и время."""

    print("mcp_record_time")
    print(f"office_id: {office_id}")
    print(f"product_id: {product_id}")

    # 1) Достаём primary_channel из product_id (это строка, например "1")
    primary_channel_str = product_id.split("-", 1)[0]
    print(f"primary_channel: {primary_channel_str}")

    # 2) Нормализуем office_id и primary_channel к int ДЛЯ Postgres
    # (в CRM product_id остаётся строкой вида "1-xxxx")
    try:
        office_id_int = int(office_id)
    except ValueError:
        raise ValueError(f"Некорректный office_id: {office_id!r}. Ожидалось число, например '19'.")

    try:
        primary_channel_int = int(primary_channel_str)
    except ValueError:
        raise ValueError(
            f"Некорректный primary_channel в product_id: {product_id!r}. "
            f"Ожидался формат 'число-число', например '1-232324'."
        )

    # 3) Сравниваем как числа (чтобы не было сюрпризов с "01" vs "1")
    if office_id_int != primary_channel_int:
        # read_secondary_article_by_primary, судя по ошибке asyncpg, ожидает int-ы
        product_id = await read_secondary_article_by_primary(
            primary_article=product_id,              # это строка артикула "1-232324" — так и надо
            primary_channel=primary_channel_int,     # ✅ int
            secondary_channel=office_id_int,         # ✅ int
        )

    print(f"resolved product_id: {product_id}")

    # 4) Записываем в CRM (product_id должен быть строкой)
    response = await record_time_async(
        date=date,
        time=time,
        product_id=product_id,
        user_id=client_id,
        staff_id=master_id,
    )

    return response
