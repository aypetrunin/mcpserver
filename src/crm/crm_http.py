# src/crm/crm_http.py
from __future__ import annotations

"""
Общие утилиты для CRM-модулей.

Зачем нужен этот файл?
----------------------
Во многих crm_*.py раньше было:

    S = get_settings()
    URL_X = f"{S.CRM_BASE_URL.rstrip('/')}{PATH}"

Это вызывает get_settings() при импорте модуля (раньше времени).

Здесь мы делаем ЛЕНИВЫЕ функции:
- get_settings() вызывается только когда реально выполняется запрос
- URL строится на лету и не хранится глобальной константой
"""

from src.settings import get_settings


def crm_base_url() -> str:
    """Возвращает базовый URL CRM без завершающего '/'."""
    return get_settings().CRM_BASE_URL.rstrip("/")


def crm_timeout_s(fallback: float = 0.0) -> float:
    """
    Единое правило timeout:
    - если caller передал timeout>0 — используем его
    - иначе берём из settings
    """
    if fallback and fallback > 0:
        return fallback
    return float(get_settings().CRM_HTTP_TIMEOUT_S)


def crm_url(path: str) -> str:
    """
    Собирает полный URL из base_url и относительного пути.

    Пример:
        crm_url("/appointments/client/records")
    """
    base = crm_base_url()
    # path должен начинаться с '/', но на всякий случай подстрахуемся
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"
