from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import Message

from app.config import get_settings
from app.db import session_scope
from app.models import User
from app.texts import load_messages

router = Router(name="secret_word")


def _is_secret(text: str, secret: str) -> bool:
    return text.strip().casefold() == secret.strip().casefold()


@router.message(F.text)
async def maybe_secret(message: Message) -> None:
    settings = get_settings()
    messages = load_messages()
    text = message.text or ""

    if not _is_secret(text, settings.secret_word):
        await message.answer(messages.fallback.text)
        return

    from_user = message.from_user
    if from_user is not None:
        with session_scope() as db:
            user = db.get(User, from_user.id)
            if user is not None and user.secret_word_used_at is None:
                user.secret_word_used_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
                db.commit()

    reply = messages.secret_word_reply.text.format(
        first_name=from_user.first_name if from_user else "",
        free_course_url=settings.free_course_url,
    )
    await message.answer(reply)
