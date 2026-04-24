from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    admin_user_id: int = Field(0, alias="ADMIN_USER_ID")

    webinar_url: str = Field(..., alias="WEBINAR_URL")
    record_url: str = Field("", alias="RECORD_URL")
    free_course_url: str = Field(..., alias="FREE_COURSE_URL")
    secret_word: str = Field(..., alias="SECRET_WORD")

    data_dir: Path = Field(Path("./data"), alias="DATA_DIR")
    tz: str = Field("Europe/Moscow", alias="TZ")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    smoke_test: bool = Field(False, alias="SMOKE_TEST")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def db_path(self) -> Path:
        return self.data_dir / "bot.db"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
        _settings.data_dir.mkdir(parents=True, exist_ok=True)
    return _settings
