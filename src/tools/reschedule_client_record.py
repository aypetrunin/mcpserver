"""MCP-сервер для переноса записей услуг клиента."""

from typing import Any

from fastmcp import FastMCP

from ..crm.crm_reschedule_client_record import reschedule_client_record  # type: ignore


tool_record_reschedule = FastMCP(name="record_reschedule")


@tool_record_reschedule.tool(
    name="record_reschedule",
    description=(
        "Перенос (изменение) существующей записи клиента на услугу в CRM.\n\n"
        "ИСПОЛЬЗУЙ ТОЛЬКО КОГДА:\n"
        "- Клиент хочет ПЕРЕНЕСТИ запись.\n"
        "- Клиент хочет изменить дату, время, мастера или филиал.\n"
        "- Клиент говорит «перезаписаться», «поменять время», «сдвинуть запись».\n\n"
        "НЕ ИСПОЛЬЗУЙ КОГДА:\n"
        "- Клиент хочет полностью отменить или удалить запись.\n"
        "- Клиент говорит «отмените», «я не приду», «удалите запись».\n"
        "В этих случаях НУЖНО использовать инструмент `record_delete`.\n\n"
        "ПРИМЕРЫ ПОДХОДЯЩИХ ЗАПРОСОВ:\n"
        "- Перенесите мою запись на завтра.\n"
        "- Можно записаться на другое время?\n"
        "- Давайте поменяем время записи.\n"
        "- Перезапишите меня к другому мастеру.\n\n"
        "ПРИМЕРЫ НЕПОДХОДЯЩИХ ЗАПРОСОВ:\n"
        "- Отмените запись. (ИСПОЛЬЗУЙ `record_delete`)\n"
        "- Удалите мою запись. (ИСПОЛЬЗУЙ `record_delete`)\n"
        "- Я не приду. (ИСПОЛЬЗУЙ `record_delete`)\n\n"
        "ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ:\n"
        "- У клиента ДОЛЖНЫ быть указаны новая дата (date) и время (time).\n"
        "- Если дата или время не указаны, СНАЧАЛА уточни их и НЕ вызывай инструмент.\n\n"
        "ВАЖНО:\n"
        "- office_id — это ID канала / филиала (тот же смысл, что и channel_id в CRM).\n\n"
        "Args:\n"
        "- user_companychat (str, required): ID пользователя.\n"
        "- office_id (str, required): ID канала / филиала.\n"
        "- record_id (str, required): ID записи в CRM.\n"
        "- master_id (str, required): ID мастера.\n"
        "- date (str, required): YYYY-MM-DD (пример: 2025-07-22).\n"
        "- time (str, required): HH:MM (пример: 08:00, 13:00).\n\n"
        "Returns:\n"
        "- dict\n"
    ),
)
async def reschedule_record(
    user_companychat: str,
    office_id: str,
    record_id: str,
    date: str,
    time: str,
    master_id: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Перенести существующую запись клиента в CRM.

    Выполняет изменение даты, времени и/или мастера для уже созданной записи
    клиента. Используется только для переноса записи, не для её отмены или
    удаления.
    """
    try:
        return await reschedule_client_record(
            user_companychat=int(user_companychat),
            channel_id=int(office_id),
            record_id=int(record_id),
            master_id=int(master_id),
            date=date,
            time=time,
            comment=comment or "Автоперенос ботом через API",
        )
    except ValueError:
        return {"success": False, "error": "Запись не перенесена: некорректные ID."}

