"""Локальная история последних диктовок в history.jsonl.

Хранится рядом с проектом, никуда не отправляется. Можно отключить
в config.yaml (save_history: false).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import PROJECT_ROOT

HISTORY_PATH = PROJECT_ROOT / "history.jsonl"


def append(raw: str, improved: str, method: str, language: str, limit: int = 20) -> None:
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "language": language,
        "method": method,
        "raw": raw,
        "improved": improved,
    }
    try:
        lines: list[str] = []
        if HISTORY_PATH.exists():
            lines = HISTORY_PATH.read_text(encoding="utf-8").splitlines()
        lines.append(json.dumps(entry, ensure_ascii=False))
        # оставляем только последние `limit` записей
        if limit > 0:
            lines = lines[-limit:]
        HISTORY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        # история не критична — молча игнорируем сбои
        pass
