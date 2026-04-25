from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    ts_registered: Mapped[datetime] = mapped_column(DateTime)
    webinar_start_at: Mapped[datetime] = mapped_column(DateTime)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    secret_word_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)

    scheduled_messages: Mapped[list["ScheduledMessage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ScheduledMessage(Base):
    __tablename__ = "scheduled_messages"
    __table_args__ = (UniqueConstraint("user_id", "kind", name="uq_user_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(8))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True)

    user: Mapped[User] = relationship(back_populates="scheduled_messages")
