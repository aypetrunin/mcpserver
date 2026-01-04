import httpx
import logging
import httpx

from typing import Any, Literal, TypedDict, cast

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

class ErrorResponse(TypedDict):
    success: Literal[False]
    error: str

class SuccessResponse(TypedDict):
    success: Literal[True]
    message: str

ResponsePayload = ErrorResponse | SuccessResponse

BASE_URL: str = "https://httpservice.ai2b.pro"
TIMEOUT_SECONDS: float = 180.0
MAX_RETRIES: int = 3

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def go_get_client_statisics(
    phone: str,
    channel_id: str = '20',
    timeout: float = TIMEOUT_SECONDS,
) -> ResponsePayload:
    """Получение статистических данных о посещении занятий клиентов."""

    logger.info("===crm.go_get_client_statisics===")

    url = f"{BASE_URL}/appointments/go_crm/client_info"

    payload = {
        "channel_id": channel_id,
        "phone": phone
    }

    logger.info("Отправка запроса на %s с payload=%r", url, payload)

    try:
        msg_err = {"message": "Сервис GO CRM временно не работает. Овратитесь к администратору."}
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            resp_json: dict[str, Any] = response.json()
            logger.info(f"resp_json: {resp_json}")

    except (httpx.TimeoutException, httpx.ConnectError) as e:
        msg = f"Сетевая ошибка при доступе к серверу {url} с payload={payload!r}: {e}"
        logger.exception(msg)
        return ErrorResponse(success=False, error=msg_err)
    
    except httpx.HTTPError as e:
        msg = f"HTTP-ошибка при доступе к серверу {url} с payload={payload!r}: {e}"
        logger.exception(msg)
        return ErrorResponse(success=False, error=msg_err)
    
    except Exception as e:  # noqa: BLE001
        msg = f"Неожиданная ошибка при доступе к серверу {url} с payload={payload!r}: {e}"
        logger.exception(msg)
        return  ErrorResponse(success=False, error=msg_err)

    if not bool(resp_json.get("success")):
        msg = f"Нет данных в системе для channel_id={channel_id}, phone={phone}",
        logger.warning(msg)
        return ErrorResponse(success=False, error=msg_err)

    if resp_json.get("abonements") == [] and resp_json.get("visits") == []:
        msg = {"message": "У Вас еще нет посещений, абонемент начнет действовать с даты первого посещения в течении 30 дней."}
    else:
        msg= resp_json
        logger.info(f"go_get_client_statisics - resp_json: {resp_json}")
        # Начало действия абонемента
        visits = resp_json.get("visits", [])
        calc = AbonementCalculator(visits)
        msg = calc.calculate()
        logger.info(f"msg: {msg}")


    return SuccessResponse(
        success=True,
        message=msg,
    )


import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dateutil.relativedelta import relativedelta


class AbonementCalculator:
    DATE_FMT = "%d.%m.%Y"
    RE_ABONEMENT = re.compile(r"х(\d+)\s*№(\d+)")

    def __init__(self, records: List[Dict[str, Any]]):
        self.records = records

    # ---------- helpers ----------
    def _parse_date(self, s: str) -> Optional[datetime]:
        return datetime.strptime(s, self.DATE_FMT) if s else None

    def _format_date(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.strftime(self.DATE_FMT) if dt else None

    def _find_start_record(self) -> Optional[Dict[str, Any]]:
        # предпочтительно is_start, но поддержим и comment == 'СТАРТ'
        return next((r for r in self.records if r.get("is_start") or r.get("comment") == "СТАРТ"), None)

    def _parse_abonement_text(self, text: str) -> tuple[Optional[int], Optional[str]]:
        m = self.RE_ABONEMENT.search(text or "")
        if not m:
            return None, None
        return int(m.group(1)), m.group(2)

    def _is_lesson(self, r: Dict[str, Any]) -> bool:
        # “занятие”, а не старт/финиш/отработка
        return (not r.get("is_start")) and (not r.get("is_finish")) and (not r.get("is_makeup"))

    # ---------- core ----------
    def calculate(self) -> Dict[str, Any]:
        start_record = self._find_start_record()

        summary: Dict[str, Any] = {
            "abonement_number": None,
            "lessons_total": None,
            "start_date": None,
            "end_date": None,

            "used_lessons": 0,          # списано из абонемента
            "remaining_lessons": None,  # осталось всего (по числу занятий)

            "makeup_lessons": 0,        # отработки (не списывают)

            "transfers_used": 0,        # переносы (занятия после конца абонемента)
            "transfers_left": None,     # сколько переносов ещё можно сделать (из остатка занятий)
            "next_transfer_after": None # дата, после которой можно переносить следующее занятие
        }

        if not start_record:
            return summary

        # 1) парсим абонемент
        lessons_total, abonement_number = self._parse_abonement_text(start_record.get("abonement", ""))
        summary["lessons_total"] = lessons_total
        summary["abonement_number"] = abonement_number

        # 2) даты
        start_dt = self._parse_date(start_record.get("date"))
        summary["start_date"] = self._format_date(start_dt)
        end_dt = start_dt + timedelta(days=30) if start_dt else None
        summary["end_date"] = self._format_date(end_dt)

        # если нет даты окончания — дальше считать бессмысленно
        if not end_dt:
            return summary

        # 3) подсчёты занятий
        used = 0
        makeup = 0
        transfer_dates: List[datetime] = []

        for r in self.records:
            dt = self._parse_date(r.get("date"))

            # отработки
            if r.get("is_makeup"):
                makeup += 1
                continue

            # старт/финиш не считаем как занятие
            if r.get("is_start") or r.get("is_finish"):
                continue

            # обычное занятие (списываем)
            used += 1

            # перенос = занятие после окончания абонемента
            if dt and dt > end_dt:
                transfer_dates.append(dt)

        transfer_dates.sort()

        summary["used_lessons"] = used
        summary["makeup_lessons"] = makeup
        summary["transfers_used"] = len(transfer_dates)

        if lessons_total is not None:
            summary["remaining_lessons"] = max(lessons_total - used, 0)
            # переносить можно только из оставшихся занятий (по твоему описанию)
            summary["transfers_left"] = max(summary["remaining_lessons"] - summary["transfers_used"], 0)

        # 4) дата, после которой можно переносить следующее занятие
        transfers_used = summary["transfers_used"]
        if transfers_used == 0:
            next_after = end_dt  # если нужно "со следующего дня": end_dt + timedelta(days=1)
        elif transfers_used == 1:
            next_after = transfer_dates[-1]
        else:
            next_after = end_dt + relativedelta(months=1)

        summary["next_transfer_after"] = self._format_date(next_after)

        return summary
