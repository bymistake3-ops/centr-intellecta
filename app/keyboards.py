from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def url_button(text: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, url=url)]])
