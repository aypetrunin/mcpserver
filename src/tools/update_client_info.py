"""MCP-сервер для записи и обновления анкетных данных клиента."""

from typing import Any

from fastmcp import FastMCP

from ..crm.crm_update_client_info import go_update_client_info  # type: ignore


tool_update_client_info = FastMCP(name="update_client_info")


@tool_update_client_info.tool(
    name="update_client_info",
    description=(
        "Сохранение и обновление анкетных данных клиента.\n\n"
        "**Назначение:**\n"
        "Используется для сохранения анкетных данных клиента при первом обращении "
        "или их обновлении в процессе онлайн-бронирования.\n\n"
        "**Args:**\n"
        "- user_id (`str`, required): ID клиента.\n"
        "- channel_id (`str`, required): ID канала.\n"
        "- parent_name (`str`, required): Имя родителя ребёнка.\n"
        "- phone (`str`, required): Телефон клиента.\n"
        "- email (`str`, required): Электронная почта клиента.\n"
        "- child_name (`str`, required): Имя ребёнка.\n"
        "- child_date_of_birth (`str`, required): Дата рождения ребёнка (DD.MM.YYYY).\n"
        "- contact_reason (`str`, required): Причина обращения.\n\n"
        "**Returns:**\n"
        "- `dict`: Результат сохранения анкетных данных.\n"
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
    """Сохранить анкетные данные клиента."""
    if not parent_name:
        return {
            "success": False,
            "message": "Имя родителя не задано. Запросите имя родителя.",
        }

    if not phone:
        return {
            "success": False,
            "message": "Номер телефона не задан. Запросите номер телефона.",
        }

    if not email:
        return {
            "success": False,
            "message": "Электронная почта не задана. Запросите электронную почту.",
        }

    if not child_name:
        return {
            "success": False,
            "message": "Имя ребёнка не задано. Запросите имя ребёнка.",
        }

    if not child_date_of_birth:
        return {
            "success": False,
            "message": "Дата рождения ребёнка не задана. Запросите дату рождения ребёнка.",
        }

    response = await go_update_client_info(
        user_id=user_id,
        channel_id=channel_id,
        parent_name=parent_name,
        phone=phone,
        email=email,
        child_name=child_name,
        child_date_of_birth=child_date_of_birth,
        contact_reason=contact_reason,
    )

    return response
