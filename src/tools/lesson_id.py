"""MCP-сервер фиксирующий выбранную клиентом услугу в базе данных."""


from fastmcp import FastMCP


tool_remember_lesson_id = FastMCP(name="remember_lesson_id")


@tool_remember_lesson_id.tool(
    name="remember_lesson_id",
    description=(
        """
        Выбор клиентом нужного урока для перноса.
        Пример: Перенесем урок с 15 января на 17 февраля
                 
        **Args:**\n
        "- phone(str): телефон клиента. **Обязательный параметр.**\n"
        "- channel_id (str): id учебной организации. **Обязательный параметр.**\n\n"
        "- record_id (str): id урока который нужно перенести. **Обязательный параметр.**\n\n"
        "- teacher (str): имя учителя урока который нужно перенести.**\n\n"
        "- new_date (str): новая дата урока.**\n\n"
        "- new_time (str): новое время урока. **Обязательный параметр.**\n\n"
        "- service (str): название урока **Обязательный параметр.**\n\n"
        "- reason (str): причина переноса урока **Обязательный параметр**\n\n"
        **Returns:**\n
        - dict: словарь с выбранными данными.
        """
    ),
)
async def remember_lesson_id(
    phone: str,
    channel_id: str,
    record_id: str,
    teacher: str,
    new_date: str,
    new_time: str,
    service: str,
    reason: str
) -> dict[str, str]:
    """Функция фиксации выбранной услуги клиентом."""
    return {
        "phone": phone,
        "channel_id": channel_id,
        "record_id": record_id,
        "teacher": teacher,
        "new_date": new_date,
        "new_time": new_time,
        "service": service,
        "reason": reason
    }
