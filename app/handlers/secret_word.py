from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from aiogram import F, Router
from aiogram.types import FSInputFile, Message

from app.config import get_settings
from app.db import session_scope
from app.jobs.send_reminder import cancel_pending_jobs
from app.keyboards import url_button
from app.models import User
from app.texts import load_messages

log = logging.getLogger(__name__)
router = Router(name="secret_word")

CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"
SECOND_BONUS_PDF = CONTENT_DIR / "bonus2.pdf"
BONUS_PDF = CONTENT_DIR / "bonus.pdf"


def _pick_secret_pdf() -> Path | None:
    """Prefer bonus2.pdf (post-webinar bonus); fall back to bonus.pdf if owner hasn't uploaded it yet."""
    if SECOND_BONUS_PDF.exists():
        return SECOND_BONUS_PDF
    if BONUS_PDF.exists():
        return BONUS_PDF
    return None

_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _transliterate(text: str) -> str:
    return "".join(_CYR_TO_LAT.get(ch, ch) for ch in text)


def _normalize(text: str) -> set[str]:
    """Produce lowercase + transliterated variants for matching."""
    base = text.strip().casefold()
    return {base, _transliterate(base)}


def _is_secret(text: str, secret: str) -> bool:
    return bool(_normalize(text) & _normalize(secret))


@router.message(F.text)
async def maybe_secret(message: Message) -> None:
    settings = get_settings()
    messages = load_messages()
    text = message.text or ""
    from_user = message.from_user

    if not _is_secret(text, settings.secret_word):
        await message.answer(messages.fallback.text)
        return

    if from_user is not None:
        with session_scope() as db:
            user = db.get(User, from_user.id)
            if user is not None and user.secret_word_used_at is None:
                user.secret_word_used_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
                db.commit()

        cancel_pending_jobs(from_user.id)
        log.info("user %s activated secret word — remaining jobs cancelled", from_user.id)

    reply_text = messages.secret_word_reply.text.format(
        first_name=from_user.first_name if from_user else "",
        course_url=settings.course_url,
    )
    markup = url_button(messages.secret_word_reply.button_text, settings.course_url)
    await message.answer(reply_text, reply_markup=markup)

    pdf = _pick_secret_pdf()
    if pdf is not None:
        await message.answer_document(
            document=FSInputFile(pdf),
            caption=messages.secret_word_reply.checklist_caption,
        )
        if pdf != SECOND_BONUS_PDF:
            log.info("bonus2.pdf missing — sent bonus.pdf as fallback")
    else:
        log.warning("no PDF found in content/ — skipping attachment")
