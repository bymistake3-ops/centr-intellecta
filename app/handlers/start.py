from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, Message, ReplyKeyboardRemove

from app.config import get_settings
from app.db import session_scope
from app.keyboards import contact_keyboard
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

PDF_PATH = Path(__file__).resolve().parent.parent.parent / "content" / "bonus.pdf"
SEND_REMINDER_REF = "app.jobs.send_reminder:send_reminder"


class RegistrationFSM(StatesGroup):
    waiting_for_contact = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    messages = load_messages()
    user_id = message.from_user.id if message.from_user else 0

    with session_scope() as db:
        existing = db.get(User, user_id)

    if existing is not None:
        text = messages.already_registered.text.format(
            first_name=existing.first_name or "",
            webinar_date=format_webinar_date_msk(
                existing.webinar_start_at.replace(tzinfo=timezone.utc)
            ),
            webinar_time=format_webinar_time_msk(
                existing.webinar_start_at.replace(tzinfo=timezone.utc)
            ),
        )
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    await state.set_state(RegistrationFSM.waiting_for_contact)
    await message.answer(messages.welcome.text.split("\n", 1)[0], reply_markup=contact_keyboard())


@router.message(RegistrationFSM.waiting_for_contact, F.contact)
async def got_contact(message: Message, state: FSMContext) -> None:
    settings = get_settings()
    messages = load_messages()
    contact = message.contact
    from_user = message.from_user
    if contact is None or from_user is None:
        return

    if contact.user_id != from_user.id:
        await message.answer("Пожалуйста, поделись своим собственным контактом.")
        return

    ts_utc = now_utc()
    webinar_utc = compute_webinar_start_at(ts_utc, messages.timings)

    with session_scope() as db:
        user = db.get(User, from_user.id)
        if user is None:
            user = User(
                user_id=from_user.id,
                username=from_user.username,
                first_name=from_user.first_name or "",
                phone=contact.phone_number or "",
                ts_registered=ts_utc.replace(tzinfo=None),
                webinar_start_at=webinar_utc.replace(tzinfo=None),
                is_blocked=False,
            )
            db.add(user)
            db.commit()

    if settings.smoke_test:
        touches = compute_smoke_schedule(ts_utc)
    else:
        touches = compute_prod_schedule(ts_utc, webinar_utc, messages.timings)
    touches = filter_future(touches, ts_utc)

    _schedule_touches(from_user.id, touches)

    welcome_text = messages.welcome.text.format(
        first_name=from_user.first_name or "",
        webinar_date=format_webinar_date_msk(webinar_utc),
        webinar_time=format_webinar_time_msk(webinar_utc),
        webinar_url=settings.webinar_url,
        record_url=settings.record_url,
        free_course_url=settings.free_course_url,
    )

    if PDF_PATH.exists():
        await message.answer_document(
            document=FSInputFile(PDF_PATH),
            caption=welcome_text,
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        log.warning("bonus.pdf not found at %s — sending welcome without attachment", PDF_PATH)
        await message.answer(welcome_text, reply_markup=ReplyKeyboardRemove())

    await state.clear()


@router.message(RegistrationFSM.waiting_for_contact)
async def waiting_hint(message: Message) -> None:
    messages = load_messages()
    await message.answer(messages.waiting_contact_hint.text, reply_markup=contact_keyboard())


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
