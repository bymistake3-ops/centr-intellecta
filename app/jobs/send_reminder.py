from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select

from app.bot import get_bot
from app.config import get_settings
from app.db import session_scope
from app.models import ScheduledMessage, User
from app.scheduler import get_scheduler
from app.texts import load_messages
from app.timing import (
    ALL_KINDS,
    format_webinar_date_msk,
    format_webinar_time_msk,
    job_id_for,
)

log = logging.getLogger(__name__)


def _mark_sent(user_id: int, kind: str, error: str | None = None) -> None:
    with session_scope() as db:
        row = db.execute(
            select(ScheduledMessage).where(
                ScheduledMessage.user_id == user_id,
                ScheduledMessage.kind == kind,
            )
        ).scalar_one_or_none()
        if row is None:
            return
        row.sent_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        row.status = "failed" if error else "sent"
        row.error = error
        db.commit()


def _cancel_pending_jobs(user_id: int) -> None:
    scheduler = get_scheduler()
    for kind in ALL_KINDS:
        try:
            scheduler.remove_job(job_id_for(user_id, kind))
        except Exception:
            pass


async def send_reminder(user_id: int, kind: str) -> None:
    settings = get_settings()
    messages = load_messages()
    bot = get_bot()

    with session_scope() as db:
        user = db.get(User, user_id)
        if user is None:
            log.warning("send_reminder: user %s not found", user_id)
            return
        if user.is_blocked:
            log.info("send_reminder: user %s blocked, skipping %s", user_id, kind)
            return
        first_name = user.first_name or ""
        webinar_start_utc = user.webinar_start_at.replace(tzinfo=timezone.utc)

    template = getattr(messages.reminders, kind).text
    text = template.format(
        first_name=first_name,
        webinar_date=format_webinar_date_msk(webinar_start_utc),
        webinar_time=format_webinar_time_msk(webinar_start_utc),
        webinar_url=settings.webinar_url,
        record_url=settings.record_url,
        free_course_url=settings.free_course_url,
    )

    try:
        await bot.send_message(chat_id=user_id, text=text)
        _mark_sent(user_id, kind)
        log.info("sent %s to %s", kind, user_id)
    except TelegramForbiddenError:
        log.info("user %s blocked bot, marking and cancelling remaining jobs", user_id)
        with session_scope() as db:
            user = db.get(User, user_id)
            if user is not None:
                user.is_blocked = True
                db.commit()
        _mark_sent(user_id, kind, error="TelegramForbiddenError")
        _cancel_pending_jobs(user_id)
    except TelegramRetryAfter as e:
        log.warning("flood control for %s: retry after %s", user_id, e.retry_after)
        _mark_sent(user_id, kind, error=f"retry_after={e.retry_after}")
    except Exception as e:  # noqa: BLE001
        log.exception("failed to send %s to %s", kind, user_id)
        _mark_sent(user_id, kind, error=str(e)[:500])
