"""MCP-сервер фиксирующий выбранную клиентом услугу в базе данных."""

from typing import Any
from fastmcp import FastMCP

from ..postgres.postgres_util import get_product_name_for_id  # type: ignore

tool_remember_product_id = FastMCP(name="remember_product_id")


from typing import Any

@tool_remember_product_id.tool(
    name="remember_product_id",
    description=(
        """
        Подтверждение/выбор клиентом нужной услуги.
        Пример: Выбираю LPG-массаж. Запишите на эпиляцию ног. Хочу стрижку модельную.

        **Args:**
        - session_id (str): id dialog session. Обязательный параметр.
        - product_id (str): id выбранной услуги. Обязательный параметр. Формат ("2-113323232")
        - product_name (str): название выбранной услуги. Обязательный параметр.

        **Returns:**
        - dict: {success: bool, message?: str, products?: list}
        """
    ),
)
async def remember_product_id(
    session_id: str,
    product_id: str,
    product_name: str,
) -> dict[str, Any]:
    """Фиксация выбранной услуги клиентом. Возвращает выбранный product_id и product_name."""
    try:
        fail_resp = {
            "success": False,
            "message": "Ошибка в выборе услуги. Покажи заново найденные услуги.",
        }

        product_name_for_id = await get_product_name_for_id(product_id=product_id)
        if product_name_for_id is None:
            return fail_resp

        # Нормализация для сравнения
        if product_name_for_id.strip().casefold() != product_name.strip().casefold():
            return fail_resp

        return {
            "success": True,
            "products": [{"product_id": product_id, "product_name": product_name_for_id}],
        }

    except Exception as e:
        raise RuntimeError(f"Ошибка remember_product_id: {e}") from e
