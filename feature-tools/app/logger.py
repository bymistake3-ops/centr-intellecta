"""Простой логгер с человеко-понятными сообщениями.

Печатает аккуратные строки в консоль. Дополнительно умеет
показывать "дружелюбные" ошибки — без технического жаргона.
"""

from __future__ import annotations

import sys
from datetime import datetime

# ANSI-цвета (в macOS Terminal работают из коробки)
_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _line(color: str, tag: str, msg: str) -> None:
    print(f"{_DIM}{_ts()}{_RESET} {color}{tag}{_RESET} {msg}", flush=True)


def info(msg: str) -> None:
    _line(_CYAN, "•", msg)


def ok(msg: str) -> None:
    _line(_GREEN, "✓", msg)


def warn(msg: str) -> None:
    _line(_YELLOW, "!", msg)


def error(msg: str) -> None:
    _line(_RED, "✗", msg)


def title(msg: str) -> None:
    """Крупный заголовок."""
    print(f"\n{_BOLD}{msg}{_RESET}", flush=True)


def block(label: str, text: str, color: str = _CYAN) -> None:
    """Показать блок текста (например, транскрибацию)."""
    print(f"\n{color}{_BOLD}{label}{_RESET}", flush=True)
    print(text if text.strip() else f"{_DIM}(пусто){_RESET}", flush=True)


def friendly_error(msg: str, hint: str | None = None) -> None:
    """Ошибка простым языком + подсказка, что делать."""
    print(f"\n{_RED}{_BOLD}Что-то пошло не так:{_RESET} {msg}", file=sys.stderr, flush=True)
    if hint:
        print(f"{_YELLOW}Что делать:{_RESET} {hint}", file=sys.stderr, flush=True)
