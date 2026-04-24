from __future__ import annotations

import logging
from datetime import timezone
from pathlib import Path

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message

from app.config import get_settings
from app.db import session_scope
from app.models import ScheduledMessage, User
from app.scheduler import get_scheduler
from app.texts import load_messages
from app.timing import (
    ScheduledTouch,
    compute_prod_schedule,
    compute_smoke_schedule,
    compute_webinar_start_at,
    filter_future,
    format_webinar_date_msk,
    format_webinar_time_msk,
    job_id_for,
    now_utc,
)

log = logging.getLogger(__name__)
router = Router(name="start")

BONUS_PDF = Path(__file__).resolve().parent.parent.parent / "content" / "bonus.pdf"
SEND_REMINDER_REF = "app.jobs.send_reminder:send_reminder"


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    settings = get_settings()
    messages = load_messages()
    if message.from_user is None:
        return
    user_id = message.from_user.id

    with session_scope() as db:
        existing = db.get(User, user_id)
        first_name_existing = existing.first_name if existing else ""
        webinar_existing = (
            existing.webinar_start_at.replace(tzinfo=timezone.utc) if existing else None
        )

    if existing is not None and webinar_existing is not None:
        text = messages.already_registered.text.format(
            first_name=first_name_existing,
            webinar_date=format_webinar_date_msk(webinar_existing),
            webinar_time=format_webinar_time_msk(webinar_existing),
            webinar_url=settings.webinar_url,
            course_url=settings.course_url,
        )
        await message.answer(text)
        return

    ts_utc = now_utc()
    webinar_utc = compute_webinar_start_at(ts_utc, messages.timings)

    with session_scope() as db:
        user = User(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name or "",
            phone="",
            ts_registered=ts_utc.replace(tzinfo=None),
            webinar_start_at=webinar_utc.replace(tzinfo=None),
            is_blocked=False,
        )
        db.add(user)
        db.commit()

    if settings.smoke_test:
        touches = compute_smoke_schedule(ts_utc)
    else:
        touches = compute_prod_schedule(webinar_utc, messages.timings)
    touches = filter_future(touches, ts_utc)
    _schedule_touches(user_id, touches)

    params = {
        "first_name": message.from_user.first_name or "",
        "webinar_date": format_webinar_date_msk(webinar_utc),
        "webinar_time": format_webinar_time_msk(webinar_utc),
        "webinar_url": settings.webinar_url,
        "course_url": settings.course_url,
    }

    await message.answer(messages.tg1.text.format(**params))

    caption = messages.tg1a.caption.format(**params)
    if BONUS_PDF.exists():
        await message.answer_document(document=FSInputFile(BONUS_PDF), caption=caption)
    else:
        log.warning("bonus.pdf not found at %s — sending caption as text", BONUS_PDF)
        await message.answer(caption)

    log.info("registered user %s, webinar at %s UTC", user_id, webinar_utc.isoformat())


def _schedule_touches(user_id: int, touches: list[ScheduledTouch]) -> None:
    scheduler = get_scheduler()

    with session_scope() as db:
        for touch in touches:
            job_id = job_id_for(user_id, touch.kind)

            scheduler.add_job(
                SEND_REMINDER_REF,
                trigger="date",
                run_date=touch.run_at_utc,
                id=job_id,
                args=[user_id, touch.kind],
                replace_existing=True,
            )

            existing = db.query(ScheduledMessage).filter_by(job_id=job_id).one_or_none()
            if existing is None:
                db.add(
                    ScheduledMessage(
                        user_id=user_id,
                        kind=touch.kind,
                        scheduled_at=touch.run_at_utc.replace(tzinfo=None),
                        status="pending",
                        job_id=job_id,
                    )
                )
            else:
                existing.scheduled_at = touch.run_at_utc.replace(tzinfo=None)
                existing.status = "pending"
                existing.error = None
                existing.sent_at = None
        db.commit()

    log.info("scheduled %d touches for user %s", len(touches), user_id)
