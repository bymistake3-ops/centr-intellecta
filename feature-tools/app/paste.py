"""Автовставка текста в активное поле + уведомления и звуки macOS.

Вставка делается через AppleScript (osascript): эмулируем Cmd+V.
Для этого macOS требует разрешение Accessibility — если его нет,
вставка не сработает, и мы честно об этом сообщим.
"""

from __future__ import annotations

import subprocess

from . import logger


def _osascript(script: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode == 0, (proc.stderr or proc.stdout).strip()
    except FileNotFoundError:
        return False, "osascript не найден (это не macOS?)"
    except subprocess.TimeoutExpired:
        return False, "превышено время ожидания"


def paste_into_active_field() -> bool:
    """Попытаться вставить содержимое буфера в активное поле (Cmd+V)."""
    script = (
        'tell application "System Events" to keystroke "v" using command down'
    )
    ok, err = _osascript(script)
    if not ok:
        low = err.lower()
        if "not allowed" in low or "1002" in err or "assistive" in low or "accessib" in low:
            logger.warn(
                "macOS не разрешает автовставку. Дайте доступ: System Settings → "
                "Privacy & Security → Accessibility → включите Terminal (или ваш терминал)."
            )
        else:
            logger.warn(f"Автовставка не сработала: {err}")
    return ok


def notify(text: str, title: str = "Фича Инструменты") -> None:
    """Показать уведомление macOS."""
    safe = text.replace('"', "'").replace("\\", "/")
    if len(safe) > 120:
        safe = safe[:117] + "…"
    script = f'display notification "{safe}" with title "{title}"'
    _osascript(script)


def play_sound(name: str = "Tink") -> None:
    """Проиграть системный звук macOS (afplay). name: Tink, Pop, Glass и т.п."""
    path = f"/System/Library/Sounds/{name}.aiff"
    try:
        subprocess.Popen(
            ["afplay", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass  # не macOS — просто молчим
