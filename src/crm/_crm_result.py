# ============================================================================
# ПРИМЕЧАНИЕ (важно прочитать)
# ----------------------------------------------------------------------------
# Этот модуль задаёт ЕДИНЫЙ формат ответов функций во всём проекте.
#
# Любая функция, которая что-то возвращает наружу (CRM, tools, API),
# должна возвращать:
#
#   1) УСПЕХ:
#      {
#        "success": True,
#        "data": <любые данные>
#      }
#
#   2) ОШИБКУ:
#      {
#        "success": False,
#        "code": "<короткий код ошибки>",
#        "error": "<человеко-читаемое описание>"
#      }
#
# ЗАЧЕМ ЭТО НУЖНО:
# - чтобы ошибки выглядели одинаково во всех модулях
# - чтобы `error` всегда был строкой (не dict, не tuple, не Exception)
# - чтобы IDE и mypy могли проверять типы
#
# ВАЖНО:
# ❌ НЕ возвращай словари руками
# ❌ НЕ меняй тип error (он ВСЕГДА str)
# ✅ Используй ТОЛЬКО функции ok() и err()
# ============================================================================
from __future__ import annotations

from typing import Generic, Literal, TypedDict, TypeVar


T = TypeVar("T")


class ErrorPayload(TypedDict):
    """Описывает ошибку в стандартном формате."""

    success: Literal[False]
    code: str
    error: str


class OkPayload(TypedDict, Generic[T]):
    """Описывает успешный результат в стандартном формате."""

    success: Literal[True]
    data: T


Payload = ErrorPayload | OkPayload[T]


def ok(data: T) -> OkPayload[T]:
    """Возвращает успешный результат."""
    return {"success": True, "data": data}


def err(*, code: str, error: str) -> ErrorPayload:
    """Возвращает ошибку в стандартном формате."""
    return {"success": False, "code": code, "error": error}
