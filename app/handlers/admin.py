from __future__ import annotations

from datetime import date, datetime, time, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select

from app.config import get_settings
from app.db import session_scope
from app.models import User

router = Router(name="admin")


def _is_owner(message: Message) -> bool:
    settings = get_settings()
    return bool(message.from_user and message.from_user.id == settings.admin_user_id)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not _is_owner(message):
        return

    today_start = datetime.combine(date.today(), time(0, 0), tzinfo=timezone.utc).replace(tzinfo=None)

    with session_scope() as db:
        total = db.execute(select(func.count(User.user_id))).scalar_one()
        today = db.execute(
            select(func.count(User.user_id)).where(User.ts_registered >= today_start)
        ).scalar_one()
        blocked = db.execute(
            select(func.count(User.user_id)).where(User.is_blocked.is_(True))
        ).scalar_one()
        used_secret = db.execute(
            select(func.count(User.user_id)).where(User.secret_word_used_at.is_not(None))
        ).scalar_one()

    await message.answer(
        f"<b>Stats</b>\n"
        f"Всего: {total}\n"
        f"Сегодня (UTC): {today}\n"
        f"Заблокировали бота: {blocked}\n"
        f"Ввели кодовое слово: {used_secret}"
    )
