from __future__ import annotations

from typing import Literal, TypedDict, TypeVar, Generic

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

T = TypeVar("T")


class ErrorPayload(TypedDict):
    """
    Стандартный формат ошибки.

    success — всегда False
    code    — короткий машинный код ошибки (например: invalid_input, http_error)
    error   — текст ошибки ДЛЯ ЧЕЛОВЕКА (всегда строка!)
    """
    success: Literal[False]
    code: str
    error: str


class OkPayload(TypedDict, Generic[T]):
    """
    Стандартный формат успешного ответа.

    success — всегда True
    data    — полезные данные (тип зависит от функции)
    """
    success: Literal[True]
    data: T


# Payload — это "или успех, или ошибка"
Payload = ErrorPayload | OkPayload[T]


def ok(data: T) -> OkPayload[T]:
    """
    Вернуть успешный результат.

    Пример:
        return ok(["lesson1", "lesson2"])
    """
    return {
        "success": True,
        "data": data,
    }


def err(*, code: str, error: str) -> ErrorPayload:
    """
    Вернуть ошибку в стандартном формате.

    Пример:
        return err(
            code="invalid_input",
            error="Не передан параметр phone"
        )

    ВАЖНО:
    - error должен быть строкой
    - не передавай сюда dict, tuple или Exception
    """
    return {
        "success": False,
        "code": code,
        "error": error,
    }
