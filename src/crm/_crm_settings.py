"""Ленивая прокладка к CRM-настройкам из Settings."""

from __future__ import annotations

from typing import Any

from src.settings import get_settings


def __getattr__(name: str) -> Any:
    """Возвращает CRM-настройку по имени атрибута."""
    s = get_settings()
    mapping = {
        "CRM_BASE_URL": s.CRM_BASE_URL,
        "CRM_HTTP_TIMEOUT_S": s.CRM_HTTP_TIMEOUT_S,
        "CRM_HTTP_RETRIES": s.CRM_HTTP_RETRIES,
        "CRM_RETRY_MIN_DELAY_S": s.CRM_RETRY_MIN_DELAY_S,
        "CRM_RETRY_MAX_DELAY_S": s.CRM_RETRY_MAX_DELAY_S,
    }
    try:
        return mapping[name]
    except KeyError as e:
        raise AttributeError(name) from e

