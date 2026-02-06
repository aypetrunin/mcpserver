"""Ленивые утилиты для работы с CRM HTTP-настройками.

Настройки и base URL вычисляются только в момент вызова,
чтобы избежать раннего обращения к env при импорте модулей.
"""

from __future__ import annotations

from src.settings import get_settings


def crm_base_url() -> str:
    """Возвращает базовый URL CRM без завершающего слэша."""
    return get_settings().CRM_BASE_URL.rstrip("/")


def crm_timeout_s(fallback: float = 0.0) -> float:
    """Возвращает timeout запроса с учётом fallback."""
    if fallback > 0:
        return fallback
    return float(get_settings().CRM_HTTP_TIMEOUT_S)


def crm_url(path: str) -> str:
    """Собирает полный URL CRM из относительного пути."""
    base = crm_base_url()
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"

