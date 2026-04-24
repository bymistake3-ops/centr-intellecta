from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ReminderText(BaseModel):
    text: str


class Reminders(BaseModel):
    T1: ReminderText
    T2: ReminderText
    T3: ReminderText
    T4: ReminderText
    T5: ReminderText
    T6: ReminderText


class Welcome(BaseModel):
    text: str
    pdf_caption: str = ""


class SimpleText(BaseModel):
    text: str


class Timings(BaseModel):
    webinar_hour_msk: int = 19
    webinar_minute_msk: int = 0
    T1_hour_msk: int = 20
    T2_hour_msk: int = 10
    T3_minutes_before: int = 60
    T4_minutes_before: int = 5
    T5_minutes_after: int = 30
    T6_hours_after: int = 24


class MessagesConfig(BaseModel):
    welcome: Welcome
    already_registered: SimpleText
    reminders: Reminders
    secret_word_reply: SimpleText
    fallback: SimpleText
    waiting_contact_hint: SimpleText
    timings: Timings = Field(default_factory=Timings)


MESSAGES_PATH = Path(__file__).resolve().parent.parent / "content" / "messages.yaml"


@lru_cache(maxsize=1)
def load_messages() -> MessagesConfig:
    with MESSAGES_PATH.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return MessagesConfig(**raw)


def format_text(template: str, **params: object) -> str:
    return template.format(**params)
