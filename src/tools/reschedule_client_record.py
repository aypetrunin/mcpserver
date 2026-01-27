#reschedule_client_record.py
"""MCP-сервер для поиска для переноса записей услуг клиента"""

from typing import Any, Dict, Optional
from fastmcp import FastMCP

from ..crm.crm_reschedule_client_record import reschedule_client_record  # type: ignore

tool_record_reschedule = FastMCP(name="record_reschedule")

@tool_record_reschedule.tool(
    name="record_reschedule",
    description=(
        "Перенос записи на услугу в CRM.\n\n"
        "**Args:**\n"
        "- user_companychat (str, required): ID пользователя.\n"
        "- office_id (str, required): ID филиала.\n"
        "- record_id (str, required): ID записи в CRM.\n"
        "- master_id (str, required): ID мастера.\n"
        "- date (str, required): YYYY-MM-DD (пример: 2025-07-22)\n"
        "- time (str, required): HH:MM (пример: 08:00, 13:00)\n"
        "**Returns:** dict\n"
    ),
)
async def reschedule_record(
    user_companychat: str,
    office_id: str,
    record_id: str,
    date: str,
    time: str,
    master_id: str,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
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
