"""MCP-сервер для удаления записей услуг клиента"""

from typing import Any, Dict
from fastmcp import FastMCP

from ..crm.crm_delete_client_record import delete_client_record  # type: ignore

tool_record_delete = FastMCP(name="record_delete")


@tool_record_delete.tool(
    name="record_delete",
    description=(
        "Отмена (удаление) записи клиента на услугу в CRM.\n\n"
        "ИСПОЛЬЗУЙ ТОЛЬКО КОГДА:\n"
        "- Клиент хочет полностью ОТКАЗАТЬСЯ от услуги.\n"
        "- Клиент просит отменить, удалить, аннулировать запись.\n"
        "- Клиент говорит, что не придёт и запись больше не нужна.\n\n"
        "НЕ ИСПОЛЬЗУЙ КОГДА:\n"
        "- Клиент хочет изменить дату, время, мастера или филиал.\n"
        "- Клиент говорит «перенести», «поменять время», «перезаписаться».\n"
        "- Клиент хочет записаться на другое время вместо текущего.\n"
        "В этих случаях НУЖНО использовать инструмент `record_reschedule`.\n\n"
        "ПРИМЕРЫ ПОДХОДЯЩИХ ЗАПРОСОВ:\n"
        "- Отмени мою запись.\n"
        "- Удали запись на массаж.\n"
        "- Я не приду, отмените запись.\n"
        "- Аннулируйте запись на сегодня.\n\n"
        "ПРИМЕРЫ НЕПОДХОДЯЩИХ ЗАПРОСОВ:\n"
        "- Можно на час позже? (ИСПОЛЬЗУЙ `record_reschedule`)\n"
        "- Давайте перенесем на завтра. (ИСПОЛЬЗУЙ `record_reschedule`)\n"
        "- Запишите меня на другое время. (ИСПОЛЬЗУЙ `record_reschedule`)\n\n"
        "ВАЖНО:\n"
        "- Если формулировка пользователя двусмысленная (например: «не получится», "
        "«можно изменить?»), СНАЧАЛА уточни намерение и НЕ вызывай инструмент.\n\n"
        "Args:\n"
        "- user_companychat (str, required): ID пользователя.\n"
        "- office_id (str, required): ID канала / филиала.\n"
        "- record_id (str, required): ID записи в CRM.\n\n"
        "Returns:\n"
        "- dict\n"
    ),
)
async def delete_records(
    user_companychat: str,
    office_id: str,
    record_id: str,
) -> Dict[str, Any]:
    """Функция удаления услуги."""
    try:
        return await delete_client_record(
            user_companychat=int(user_companychat),
            office_id=int(office_id),
            record_id=int(record_id),
        )
    except ValueError:
        return {
            "success": False,
            "error": "Записи не существует.",
        }
