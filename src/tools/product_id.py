"""MCP-сервер фиксирующий выбранную клиентом услугу в базе данных."""

from fastmcp import FastMCP

from ..postgres.postgres_util import insert_dialog_state

tool_record_product_id = FastMCP(name="record_product_id")


@tool_record_product_id.tool(
    name="record_product_id",
    description=(
        """
        Подтверждение/выбор клиентом нужной услуги.
        Пример: Выбираю LPG-массаж. Запишите на эпиляцию ног. Хочу стрижку моднльную.
                 
        **Args:**\n
        - session_id(str): id dialog session. **Обязательный параметр.**\n
        - product_id (str): id выбранной услуги. **Обязательный параметр.** Обязательный формат id ("2-113323232")\n
        - product_name (str): название выбранной услуги **Обязательный параметр.**\n
        **Returns:**\n
        - bool: True, если запись прошла успешно, иначе False.
        """
    ),
)
async def record_product_id(
    session_id: str, product_id: str, product_name: str
) -> bool:
    """Функция фиксации выбранной услуги клиентом."""
    try:
        insert_dialog_state(
            session_id=session_id,
            product_id={"product_id": product_id, "product_name": product_name},
            name="record",
        )
    except Exception:
        raise ("Ошибка 'record_product_id - {e}")

    return True
