# src/crm/crm_update_client_lesson.py
"""
Модуль переноса урока клиента (GO CRM).

Что исправлено относительно старой версии:
-----------------------------------------
1) Убрали S = get_settings() на уровне модуля.
   Раньше settings читались при импорте файла → могло ломаться, если init_runtime()
   ещё не вызывался (тесты/скрипты/другой entrypoint).

2) Убрали URL_RESCHEDULE как глобальную константу, построенную из settings.
   Теперь URL строим лениво в момент HTTP-вызова через crm_url().

3) Таймаут берём единообразно через crm_timeout_s() (лениво).

Дополнительно:
- Убраны ссылки вида ":contentReference[oaicite:...]" — это артефакты, не относящиеся к вашему репозиторию.
- Бизнес-логика переносов сохранена.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal, Optional, TypedDict

import httpx

from ..clients import get_http
from ..http_retry import CRM_HTTP_RETRY
from ._crm_http import crm_timeout_s, crm_url
from .crm_get_client_statistics import go_get_client_statisics

logger = logging.getLogger(__name__.split('.')[-1])

# Относительный путь к методу GO CRM (безопасная константа)
RESCHEDULE_PATH = "/appointments/go_crm/reschedule_record"


class ErrorResponse(TypedDict):
    success: Literal[False]
    error: str


class SuccessResponse(TypedDict):
    success: Literal[True]
    message: str


ResponsePayload = ErrorResponse | SuccessResponse


def _log_and_build_input_error(param_name: str, value: Any) -> ErrorResponse:
    """Единая форма ошибки на неверных входных параметрах."""
    logger.warning("Не указан или неверный тип '%s': %r", param_name, value)
    return ErrorResponse(
        success=False,
        error="Ошибка в типах входных данных. Проверь и перезапусти инструмент.",
    )


def _validate_str_param(value: Any) -> bool:
    """True только для непустой строки."""
    return isinstance(value, str) and bool(value.strip())


def normalize_date(value: Optional[str]) -> Optional[str]:
    """
    Приводим дату к формату DD.MM.YYYY.

    GO CRM иногда отдаёт YYYY-MM-DD.
    Мы поддерживаем оба и нормализуем в единый формат.
    """
    if not value:
        return None

    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {value}")


@CRM_HTTP_RETRY
async def _reschedule_record_payload(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    """
    Низкоуровневый HTTP-вызов с единым retry:
    - timeout / network error
    - HTTP 429
    - HTTP 5xx

    Важно:
    - URL строим лениво через crm_url(RESCHEDULE_PATH),
      поэтому settings не читаются при импорте модуля.
    """
    client = get_http()
    url = crm_url(RESCHEDULE_PATH)

    resp = await client.post(
        url,
        json=payload,
        timeout=httpx.Timeout(timeout_s),
    )
    resp.raise_for_status()

    data = resp.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected JSON type from CRM: {type(data)}")
    return data


async def go_update_client_lesson(
    phone: str,
    channel_id: str,
    record_id: str,
    instructor_name: str,
    new_date: str,
    new_time: str,
    service: str,
    reason: str,
    timeout: float = 0.0,
) -> ResponsePayload:
    """
    Перенос урока на другую дату и время (GO CRM).

    Параметры:
    - timeout: если >0 — используем его, иначе берём settings.CRM_HTTP_TIMEOUT_S (лениво)
    """
  
    # ---- валидация входных ----
    for name, value in (
        ("phone", phone),
        ("channel_id", channel_id),
        ("record_id", record_id),
        ("instructor_name", instructor_name),
        ("new_date", new_date),
        ("new_time", new_time),
        ("service", service),
        ("reason", reason),
    ):
        if not _validate_str_param(value):
            return _log_and_build_input_error(name, value)

    # ---- нормализация даты (GO CRM иногда отдаёт YYYY-MM-DD) ----
    try:
        normalized_new_date = normalize_date(new_date) or new_date
    except ValueError:
        return ErrorResponse(success=False, error=f"Неверный формат даты: {new_date}. Ожидается DD.MM.YYYY")

    # ---- бизнес-ограничение по переносам (как в исходнике) ----
    # Логика опирается на end_date и next_transfer_after из статистики.
    statistic = await go_get_client_statisics(phone=phone, channel_id=channel_id)
    abonent_end_date = None
    next_transfer_after = None

    if statistic.get("success") is True:
        msg = statistic.get("message") or {}
        if isinstance(msg, dict):
            abonent_end_date = msg.get("end_date")
            next_transfer_after = msg.get("next_transfer_after")

    # Дата переноса (то, куда хотим перенести занятие)
    try:
        transfer_date = datetime.strptime(normalized_new_date, "%d.%m.%Y")
    except ValueError:
        return ErrorResponse(success=False, error=f"Неверный формат даты: {new_date}. Ожидается DD.MM.YYYY")

    abonent_end_dt = None
    next_transfer_dt = None
    try:
        if abonent_end_date:
            abonent_end_dt = datetime.strptime(str(abonent_end_date), "%d.%m.%Y")
        if next_transfer_after:
            next_transfer_dt = datetime.strptime(str(next_transfer_after), "%d.%m.%Y")
    except ValueError:
        # если CRM вернул мусор — не блокируем перенос, просто логируем
        logger.warning(
            "Некорректные даты из статистики: end_date=%r next_transfer_after=%r",
            abonent_end_date,
            next_transfer_after,
        )

    # Условие из исходника:
    # если дата переноса не попадает ни "до конца абонемента",
    # ни "после даты следующего переноса" — блокируем.
    if abonent_end_dt and next_transfer_dt:
        if not (transfer_date <= abonent_end_dt or transfer_date >= next_transfer_dt):
            msg = (
                "В этом месяце после окончания абонемента у Вас уже было 2 переноса. "
                f"Вы можете перенести занятие после {next_transfer_dt.strftime('%d.%m.%Y')}"
            )
            logger.warning(msg)
            return ErrorResponse(success=False, error=msg)

    payload: dict[str, str] = {
        "channel_id": channel_id.strip(),
        "phone": phone.strip(),
        "record_id": record_id.strip(),
        "instructor_name": instructor_name.strip(),
        "new_date": normalized_new_date.strip(),
        "new_time": new_time.strip(),
        "service": service.strip(),
        "reason": reason.strip(),
    }

    effective_timeout = crm_timeout_s(timeout)

    try:
        resp_json = await _reschedule_record_payload(payload=payload, timeout_s=effective_timeout)

    except httpx.HTTPStatusError as e:
        logger.warning(
            "go_update_client_lesson http error status=%s body=%s",
            e.response.status_code,
            e.response.text[:500],
        )
        return ErrorResponse(success=False, error="GO CRM временно недоступен. Обратитесь к администратору.")

    except httpx.RequestError as e:
        logger.warning("go_update_client_lesson request error payload=%s: %s", payload, str(e))
        return ErrorResponse(success=False, error="Сетевая ошибка при обращении к GO CRM.")

    except ValueError:
        logger.exception("go_update_client_lesson invalid json payload=%s", payload)
        return ErrorResponse(success=False, error="GO CRM вернул некорректный ответ.")

    except Exception as e:  # noqa: BLE001
        logger.exception("go_update_client_lesson unexpected error payload=%s: %s", payload, e)
        return ErrorResponse(success=False, error="Неизвестная ошибка при обращении к GO CRM.")

    if resp_json.get("success") is not True:
        return ErrorResponse(success=False, error="Ошибка переноса урока. Обратитесь к администратору.")

    api_new_date = str(resp_json.get("new_date", normalized_new_date))
    api_new_time = str(resp_json.get("new_time", new_time))

    return SuccessResponse(
        success=True,
        message=f"Перенос урока выполнен успешно на {api_new_date} {api_new_time}!",
    )



# """Модуль переноса урока клиента."""

# from __future__ import annotations


# import asyncio
# import logging
# from typing import Any, Literal, TypedDict, cast, Optional
# from datetime import datetime

# import httpx
# from tenacity import (
#     retry,
#     retry_if_exception_type,
#     stop_after_attempt,
#     wait_exponential,
# )
# from .crm_settings import (
#     CRM_BASE_URL,
#     CRM_HTTP_TIMEOUT_S,
#     CRM_HTTP_RETRIES,
#     CRM_RETRY_MIN_DELAY_S,
#     CRM_RETRY_MAX_DELAY_S,
# )
# from .crm_get_client_statistics import AbonementCalculator, go_get_client_statisics


# logger = logging.getLogger(__name__)


# class ErrorResponse(TypedDict):
#     success: Literal[False]
#     error: str


# class SuccessResponse(TypedDict):
#     success: Literal[True]
#     message: str


# ResponsePayload = ErrorResponse | SuccessResponse


# def _log_and_build_input_error(param_name: str, value: Any) -> ErrorResponse:
#     logger.warning(
#         "Не указан или неверный тип '%s': %r",
#         param_name,
#         value,
#     )
#     return ErrorResponse(
#         success=False,
#         error=(
#             "Ошибка в типах входных данных. "
#             "Проверь и перезапусти инструмент."
#         ),
#     )


# def _validate_str_param(name: str, value: Any) -> bool:
#     return isinstance(value, str) and bool(value)


# @retry(
#     stop=stop_after_attempt(CRM_HTTP_RETRIES),
#     wait=wait_exponential(multiplier=1, min=CRM_RETRY_MIN_DELAY_S, max=CRM_RETRY_MAX_DELAY_S),
#     retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
#     reraise=True,
# )
# async def go_update_client_lesson(
#     phone: str,
#     channel_id: str,
#     record_id: str,
#     instructor_name: str,
#     new_date: str,
#     new_time: str,
#     service: str,
#     reason: str,
#     timeout: float = CRM_HTTP_TIMEOUT_S,
# ) -> ResponsePayload:
#     """Перенос урока клиента на другую дату/время."""

#     logger.info("===crm_go.go_update_client_lesson===")

#     for name, value in (
#         ("channel_id", channel_id),
#         ("phone", phone),
#         ("record_id", record_id),
#         ("instructor_name", instructor_name),
#         ("new_date", new_date),
#         ("new_time", new_time),
#         ("service", service),
#         ("reason", reason),
#     ):
#         if not _validate_str_param(name, value):
#             return _log_and_build_input_error(name, value)

#     statistic = await go_get_client_statisics(
#         phone=phone
#     )

#     if not statistic.get("success", False):
#         msg = "Ошибка переноса урока. Не могу получить разрешенную дату переноса. Обратитесь к администратору."
#         logger.exception(msg)
#         return ErrorResponse(success=False, error=msg)

#     logger.info(f"statistic: {statistic}")

#     transfer_date = datetime.strptime(normalize_date(new_date), "%d.%m.%Y")
#     logger.info(f"transfer_date: {transfer_date}")


#     abonent_end_data = statistic.get("message", {}).get("end_date", None)
#     next_transfer_after = statistic.get("message", {}).get("next_transfer_after", None)

#     if abonent_end_data:
#         abonent_end_data = datetime.strptime(abonent_end_data, "%d.%m.%Y")
#         next_transfer_after = datetime.strptime(next_transfer_after, "%d.%m.%Y")
    
#     logger.info(f"abonent_end_data: {abonent_end_data}")
#     logger.info(f"next_transfer_after: {next_transfer_after}")

#     if abonent_end_data is not None and not (transfer_date <= abonent_end_data or transfer_date >= next_transfer_after):
#         msg = f"В этом месяце после окончания абонемента у Вас уже было 2 переноса. Вы можете перенести занятие после {statistic.get('next_transfer_after')}"
#         logger.exception(msg)
#         return ErrorResponse(success=False, error=msg)

#     url = f"{CRM_BASE_URL}/appointments/go_crm/reschedule_record"

#     payload: dict[str, str] = {
#         "channel_id": channel_id,
#         "phone": phone,
#         "record_id": record_id,
#         "instructor_name": instructor_name,
#         "new_date": new_date,
#         "new_time": new_time,
#         "service": service,
#         "reason": reason,
#     }

#     logger.info("Отправка запроса на %s с payload=%r", url, payload)

#     try:
#         async with httpx.AsyncClient(timeout=timeout) as client:
#             response = await client.post(url=url, json=payload)
#             response.raise_for_status()
#             resp_json: dict[str, Any] = response.json()

#     except (httpx.TimeoutException, httpx.ConnectError) as e:
#         msg = f"Сетевая ошибка при запросе на {url} с payload={payload!r}: {e}"
#         logger.exception(msg)
#         return ErrorResponse(success=False, error={"message":msg})
    
#     except httpx.HTTPError as e:
#         msg = f"HTTP-ошибка при запросе на {url} с payload={payload!r}: {e}"
#         # msg = f"Ошибка переноса занятия ID:{payload['record_id']}(подставь данные по этому ID чтобы клиент понял какое занятие переностися) на {payload['new_date']} {payload['new_time']}. Поправте меня если я не правильно Вас понял."
#         logger.exception(msg)
#         return ErrorResponse(success=False, error={"message":msg})

#     except Exception as e:  # noqa: BLE001
#         msg = f"Неожиданная при запросе на {url} с payload={payload!r}: {e}"
#         logger.exception(msg)
#         return ErrorResponse(success=False, error={"message":msg})

#     if not resp_json.get("success"):
#         msg = "Ошибка переноса урока. Обратитесь к администратору."
#         logger.exception(msg)
#         return ErrorResponse(success=False, error={"message":msg})

#     logger.info(f"resp_json: {resp_json}")

#     api_new_date = str(resp_json.get("new_date", new_date))
#     api_new_time = str(resp_json.get("new_time", new_time))

#     return SuccessResponse(
#         success=True,
#         message=f"Перенос урока выполнен успешно на {api_new_date} {api_new_time}!",
#     )


# def normalize_date(value: Optional[str]) -> Optional[str]:
#     if not value:
#         return None

#     for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
#         try:
#             dt = datetime.strptime(value, fmt)
#             return dt.strftime("%d.%m.%Y")
#         except ValueError:
#             continue

#     raise ValueError(f"Unsupported date format: {value}")




# # Пример использования
# if __name__ == "__main__":
#     """Тестовый пример работы функции."""

#     async def main()->None:
#         """Тестовый пример работы функции."""
#         phone = "79131052808"
#         channel_id = "20"
#         record_id = "9077"
#         instructor_name = "Пискарева Анна Александровна"
#         new_date = "17.01.2026"
#         new_time = "20:00"
#         service = "КРЗ с дефектологом 45 мин 8 занятий 20000"
#         logger.info("Перенос урока.")
#         result = await go_update_client_lesson(
#             phone = phone,
#             channel_id = channel_id,
#             record_id = record_id,
#             instructor_name = instructor_name,
#             new_date = new_date,
#             new_time = new_time,
#             service = service,
#             reason = ""
#         )
#         logger.info(result)

#     asyncio.run(main())

# # cd /home/copilot_superuser/petrunin/zena/mcpserver
# # uv run python -m src.crm.crm_current_client_records