"""Работа с буфером обмена.

На macOS используем встроенную утилиту pbcopy (ничего ставить не нужно).
Если она недоступна — пробуем pyperclip.
"""

from __future__ import annotations

import subprocess

from . import logger


def copy(text: str) -> bool:
    """Скопировать текст в буфер обмена. Вернуть True при успехе."""
    if text is None:
        text = ""

    # 1) pbcopy — родная утилита macOS
    try:
        proc = subprocess.run(
            ["pbcopy"],
            input=text.encode("utf-8"),
            check=True,
        )
        if proc.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # 2) pyperclip — кроссплатформенный запасной вариант
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warn(f"Не удалось скопировать в буфер обмена: {exc}")
        return False
