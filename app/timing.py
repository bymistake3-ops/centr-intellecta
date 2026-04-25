from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from app.texts import Timings

MSK = ZoneInfo("Europe/Moscow")

Kind = Literal["TG2", "TG3", "TG4", "TG5"]
ALL_KINDS: tuple[Kind, ...] = ("TG2", "TG3", "TG4", "TG5")


@dataclass(frozen=True)
class ScheduledTouch:
    kind: Kind
    run_at_utc: datetime


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def compute_webinar_start_at(ts_registered_utc: datetime, timings: Timings) -> datetime:
    """Next-day 19:00 MSK regardless of registration hour."""
    if ts_registered_utc.tzinfo is None:
        ts_registered_utc = ts_registered_utc.replace(tzinfo=timezone.utc)
    reg_msk = ts_registered_utc.astimezone(MSK)
    next_day: date = reg_msk.date() + timedelta(days=1)
    webinar_msk = datetime.combine(
        next_day,
        time(timings.webinar_hour_msk, timings.webinar_minute_msk),
        tzinfo=MSK,
    )
    return webinar_msk.astimezone(timezone.utc)


def compute_prod_schedule(
    webinar_start_utc: datetime,
    timings: Timings,
) -> list[ScheduledTouch]:
    webinar_msk = webinar_start_utc.astimezone(MSK)
    tg2_msk = datetime.combine(webinar_msk.date(), time(timings.TG2_hour_msk, 0), tzinfo=MSK)

    return [
        ScheduledTouch("TG2", tg2_msk.astimezone(timezone.utc)),
        ScheduledTouch("TG3", webinar_start_utc - timedelta(minutes=timings.TG3_minutes_before)),
        ScheduledTouch("TG4", webinar_start_utc - timedelta(minutes=timings.TG4_minutes_before)),
        ScheduledTouch("TG5", webinar_start_utc + timedelta(minutes=timings.TG5_minutes_after)),
    ]


def compute_smoke_schedule(base_utc: datetime) -> list[ScheduledTouch]:
    """All 4 touches fire 60 seconds apart — full funnel plays out in ~4 min."""
    return [
        ScheduledTouch(kind, base_utc + timedelta(seconds=60 * (i + 1)))
        for i, kind in enumerate(ALL_KINDS)
    ]


def filter_future(touches: list[ScheduledTouch], now: datetime | None = None) -> list[ScheduledTouch]:
    ref = now or now_utc()
    return [t for t in touches if t.run_at_utc > ref]


def job_id_for(user_id: int, kind: Kind) -> str:
    return f"reminder:{user_id}:{kind}"


_MONTHS_RU = (
    "",
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)


def format_webinar_date_msk(webinar_start_utc: datetime) -> str:
    msk = webinar_start_utc.astimezone(MSK)
    return f"{msk.day} {_MONTHS_RU[msk.month]}"


def format_webinar_time_msk(webinar_start_utc: datetime) -> str:
    msk = webinar_start_utc.astimezone(MSK)
    return msk.strftime("%H:%M")
