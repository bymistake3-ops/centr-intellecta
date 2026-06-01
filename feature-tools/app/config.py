"""Чтение и проверка config.yaml.

Если файла нет или какие-то поля пропущены — подставляем
разумные значения по умолчанию, чтобы сервис всё равно запустился.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - yaml ставится в install.sh
    yaml = None  # type: ignore

# Корень проекта = папка feature-tools (на уровень выше app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# Допустимые значения — для дружелюбной проверки
_VALID_PASTE_MODES = {"auto_paste", "clipboard_only", "both"}
_VALID_LANGUAGES = {"auto", "ru", "en"}
_VALID_TEXT_MODES = {"raw", "clean", "prompt_writer", "letter", "note"}
_VALID_WHISPER = {"tiny", "base", "small", "medium", "large-v3"}

# Соответствие "режим обработки" -> файл с системным промтом
TEXT_MODE_PROMPTS = {
    "clean": "clean.txt",
    "prompt_writer": "prompt_writer.txt",
    "letter": "letter.txt",
    "note": "note.txt",
}


@dataclass
class Config:
    hotkey: str = "right_option"
    language: str = "auto"
    whisper_model: str = "small"
    paste_mode: str = "both"
    use_ollama: bool = True
    ollama_model: str = "qwen2.5:7b"
    text_mode: str = "prompt_writer"

    min_record_seconds: float = 0.4
    max_record_seconds: float = 120.0
    sample_rate: int = 16000

    play_sounds: bool = True
    show_notifications: bool = True
    save_history: bool = True
    history_limit: int = 20

    warnings: list[str] = field(default_factory=list)

    # --- удобные производные значения ---

    def prompt_text(self) -> str | None:
        """Системный промт для текущего text_mode (или None для raw)."""
        fname = TEXT_MODE_PROMPTS.get(self.text_mode)
        if not fname:
            return None
        path = PROMPTS_DIR / fname
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return None

    @property
    def ollama_url(self) -> str:
        # Можно переопределить переменной окружения, по умолчанию локально
        return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def _coerce_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "да"}
    return default


def load_config(path: Path | str | None = None) -> Config:
    """Загрузить конфиг. Никогда не падает: при проблемах копит warnings."""
    cfg = Config()
    path = Path(path) if path else CONFIG_PATH

    if yaml is None:
        cfg.warnings.append(
            "Библиотека PyYAML не установлена — использую настройки по умолчанию."
        )
        return cfg

    if not path.exists():
        cfg.warnings.append(
            f"Файл config.yaml не найден ({path}) — использую настройки по умолчанию."
        )
        return cfg

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        cfg.warnings.append(f"Не смог прочитать config.yaml ({exc}). Беру значения по умолчанию.")
        return cfg

    if not isinstance(raw, dict):
        cfg.warnings.append("config.yaml имеет неверный формат — использую значения по умолчанию.")
        return cfg

    cfg.hotkey = str(raw.get("hotkey", cfg.hotkey)).strip().lower()
    cfg.language = str(raw.get("language", cfg.language)).strip().lower()
    cfg.whisper_model = str(raw.get("whisper_model", cfg.whisper_model)).strip()
    cfg.paste_mode = str(raw.get("paste_mode", cfg.paste_mode)).strip().lower()
    cfg.use_ollama = _coerce_bool(raw.get("use_ollama"), cfg.use_ollama)
    cfg.ollama_model = str(raw.get("ollama_model", cfg.ollama_model)).strip()
    cfg.text_mode = str(raw.get("text_mode", cfg.text_mode)).strip().lower()

    cfg.min_record_seconds = float(raw.get("min_record_seconds", cfg.min_record_seconds))
    cfg.max_record_seconds = float(raw.get("max_record_seconds", cfg.max_record_seconds))
    cfg.sample_rate = int(raw.get("sample_rate", cfg.sample_rate))

    cfg.play_sounds = _coerce_bool(raw.get("play_sounds"), cfg.play_sounds)
    cfg.show_notifications = _coerce_bool(raw.get("show_notifications"), cfg.show_notifications)
    cfg.save_history = _coerce_bool(raw.get("save_history"), cfg.save_history)
    cfg.history_limit = int(raw.get("history_limit", cfg.history_limit))

    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    if cfg.paste_mode not in _VALID_PASTE_MODES:
        cfg.warnings.append(
            f"paste_mode='{cfg.paste_mode}' не распознан — использую 'both'."
        )
        cfg.paste_mode = "both"
    if cfg.language not in _VALID_LANGUAGES:
        cfg.warnings.append(f"language='{cfg.language}' не распознан — использую 'auto'.")
        cfg.language = "auto"
    if cfg.text_mode not in _VALID_TEXT_MODES:
        cfg.warnings.append(
            f"text_mode='{cfg.text_mode}' не распознан — использую 'prompt_writer'."
        )
        cfg.text_mode = "prompt_writer"
    if cfg.whisper_model not in _VALID_WHISPER:
        cfg.warnings.append(
            f"whisper_model='{cfg.whisper_model}' — необычное значение, "
            "попробую загрузить как есть."
        )
