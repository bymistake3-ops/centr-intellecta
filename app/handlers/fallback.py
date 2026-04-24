from __future__ import annotations

from aiogram import Router
from aiogram.types import Message

from app.texts import load_messages

router = Router(name="fallback")


@router.message()
async def any_other(message: Message) -> None:
    messages = load_messages()
    await message.answer(messages.fallback.text)
