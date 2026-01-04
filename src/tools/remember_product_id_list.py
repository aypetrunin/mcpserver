"""MCP-сервер фиксирующий выбранную клиентом услугу в базе данных."""

from typing import Any
from fastmcp import FastMCP

from ..postgres.postgres_util import insert_dialog_state  # type: ignore

tool_remember_product_id_list = FastMCP(name="remember_product_id_list")


@tool_remember_product_id_list.tool(
    name="remember_product_id_list",
    description=(
        """
        Подтверждение/выбор клиентом нужной услуги/услуг.
        Пример: Выбираю LPG-массаж. Запишите на эпиляцию ног. Хочу стрижку модельную. Хочу Прессотерапия и Роликовый массажер. 1 и 2.
                 
        **Args:**\n
        - session_id(str): id dialog session. **Обязательный параметр.**\n
        - product_id (list[str]): id выбранной/ых услуги. **Обязательный параметр.** Обязательный формат id ("2-113323232")\n
        - product_name (list[str]): название выбранной/ых услуги **Обязательный параметр.**\n
        **Returns:**\n
        - list[dict]: Вернет не пустой список если прошло успешно.
        """
    ),
)
async def remember_product_id(
    session_id: str,
    product_id: list[str],
    product_name: list[str]
) -> list[dict[str, Any]]:
    """Функция фиксации выбранной услуги клиентом."""
    try:
        result = [
            {"product_id": v1, "product_name": v2}
            for v1, v2 in zip(product_id, product_name)
        ]

        insert_dialog_state(
            session_id=session_id,
            product_id=result,
            name="remember",
        )
    except Exception as e:
        raise RuntimeError(f"Ошибка remember_product_id: {e}")

    return result
