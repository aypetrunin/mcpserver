# _crm_result.py
# ============================================================================
# ЕДИНЫЙ формат ответов (v2)
#
# УСПЕХ:
#   {"success": True, "data": <T>}
#
# ОШИБКА:
#   {
#     "success": False,
#     "code": "<короткий код ошибки>",
#     "error": "<человеко-читаемое описание>",
#     "details": { ... }   # optional
#     "meta": { ... }      # optional (trace_id, retriable, status, etc.)
#   }
#
# Правила:
# - error ВСЕГДА str
# - details/meta — только для ошибок (опционально)
# - НЕ возвращайте словари руками: используйте ok()/err()
# ============================================================================

from __future__ import annotations

from typing import Any, Generic, Literal, NotRequired, TypeVar

from typing_extensions import TypedDict


T = TypeVar("T")


class ErrorMeta(TypedDict, total=False):
    retriable: bool
    trace_id: str
    status: int


class ErrorPayload(TypedDict):
    success: Literal[False]
    code: str
    error: str
    details: NotRequired[dict[str, Any]]
    meta: NotRequired[ErrorMeta]


class OkPayload(TypedDict, Generic[T]):
    success: Literal[True]
    data: T


Payload = ErrorPayload | OkPayload[T]


def ok(data: T) -> OkPayload[T]:
    return {"success": True, "data": data}


def err(
    *,
    code: str,
    error: str,
    details: dict[str, Any] | None = None,
    meta: ErrorMeta | None = None,
) -> ErrorPayload:
    out: ErrorPayload = {"success": False, "code": code, "error": error}
    if details:
        out["details"] = details
    if meta:
        out["meta"] = meta
    return out
