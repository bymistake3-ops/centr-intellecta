from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Welcome(BaseModel):
    text: str


class WelcomePdf(BaseModel):
    caption: str


class SimpleText(BaseModel):
    text: str


class ReminderText(BaseModel):
    text: str
    button_text: str | None = None


class Reminders(BaseModel):
    TG2: ReminderText
    TG3: ReminderText
    TG4: ReminderText
    TG5: ReminderText


class SecretWordReply(BaseModel):
    text: str
    button_text: str
    checklist_caption: str


class Timings(BaseModel):
    webinar_hour_msk: int = 19
    webinar_minute_msk: int = 0
    TG2_hour_msk: int = 10
    TG3_minutes_before: int = 30
    TG4_minutes_before: int = 5
    TG5_minutes_after: int = 90


class MessagesConfig(BaseModel):
    tg1: Welcome
    tg1a: WelcomePdf
    already_registered: SimpleText
    reminders: Reminders
    secret_word_reply: SecretWordReply
    fallback: SimpleText
    timings: Timings = Field(default_factory=Timings)


MESSAGES_PATH = Path(__file__).resolve().parent.parent / "content" / "messages.yaml"


@lru_cache(maxsize=1)
def load_messages() -> MessagesConfig:
    with MESSAGES_PATH.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return MessagesConfig(**raw)
