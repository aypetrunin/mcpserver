"""MCP-сервер для записи и обновления анкетных данных клиента."""

from typing import Any
from fastmcp import FastMCP

from ..crm.crm_update_client_info import go_update_client_info  # type: ignore

tool_update_client_info = FastMCP(name="update_client_info")

@tool_update_client_info.tool(
    name="update_client_info",
    description=(
        "Сохранение анкетных данных клиента.\n\n"
        "**Назначение:**\n"
        "Сохранение анкетных данных клиента при первом обращении."
        "Используется при онлайн-бронировании.\n\n"
        "**Args:**\n"
        "- user_id(str): id клиента. **Обязательный параметр.**\n"
        "- channel_id(str): id канала. **Обязательный параметр.**\n"
        "- parent_name (str): Имя родителя ребенка. **Обязательный параметр.**\n\n"
        "- phone(str): Телефон клиента. **Обязательный параметр.**\n"
        "- email (str): Электронная почта. **Обязательный параметр.**\n\n"
        "- child_name (str): Имя ребенка. **Обязательный параметр.**\n\n"
        "- child_date_of_birth (str): Дата рождения ребенка в формате 'DD.MM.YYYY'. **Обязательный параметр.**\n\n"
        "- contact_reason (str): Причина обращения.**\n\n"
        "**Returns:**\n"
        "dict: результат переноса"
    ),
)
async def update_client_info_go(
    user_id: str,
    channel_id: str,
    parent_name: str,
    phone: str,
    email: str,
    child_name: str,
    child_date_of_birth: str,
    contact_reason: str,
) -> dict[str, Any]:
    """Функция переноса урока."""

    if not parent_name:
        msg_error = "Имя родителя не задано. Запросить имя родителя."
        return {"success": False, "messege": msg_error}
    elif not phone:
        msg_error = "Номер телефона не задан. Запросить номер телефона."
        return {"success": False, "messege": msg_error}
    elif not email:
        msg_error = "Электронная почта не задана. Запросить электронную почту."
        return {"success": False, "messege": msg_error}
    elif not child_name:
        msg_error = "Имя ребенка не задано. Запросить имя ребенка."
        return {"success": False, "messege": msg_error}
    elif not child_date_of_birth:
        msg_error = "День рождения ребенка не задано. Запросить день рожднгия ребенка."
        return {"success": False, "messege": msg_error}

    responce = await go_update_client_info(
        user_id=user_id,
        channel_id=channel_id,
        parent_name=parent_name,
        phone=phone,
        email=email,
        child_name=child_name,
        child_date_of_birth=child_date_of_birth,
        contact_reason=contact_reason,
    )

    return responce


# {
#   "channel_id": 1,           // ID канала из БД (обязательно)
#   "child_fio": "Тест(Test2)",  (обязательно)
#   "phone": "+79876544444"  (обязательно)
  
#   "child_fio": "Тест(Test2)", // Имя ребёнка (обязательно)
#   "parent_fio": "Test(family)", // ФИО родителя (обязательно)
#   "phone": "+79876544444",     // Телефон 1 (обязательно)
#   "phone2": "",               // Телефон 2 (необязательно)
  
#   "uid": "",                  // Уникальный ID (необязательно)
#   "mail": "oi@mail.ru",       // Email (обязательно)
#   "birthday": "19.11.2025",   // ДР в формате ДД.ММ.ГГГГ (обязательно)
  
#   "center_id": 1,             // ID центра (по умолчанию 1)
#   "way_id": 20,               // ID пути (по умолчанию 20)
#   "status": "active",         // Статус (по умолчанию "active")
#   "comment": "Создан через API" // Комментарий (необязательно)
# }