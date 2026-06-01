"""Тесты для встроенного fallback-улучшателя текста.

Эти тесты НЕ требуют ни микрофона, ни Ollama, ни интернета —
проверяют только локальную очистку текста.

Запуск:
    cd feature-tools
    python -m pytest tests/ -v
или без pytest:
    python tests/test_text_enhancer.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config
from app.text_enhancer import (
    _capitalize_sentences,
    _dedupe_repeats,
    _fallback_enhance,
    _remove_fillers,
    enhance,
)


def _cfg(**kw) -> Config:
    c = Config()
    c.use_ollama = False  # форсируем fallback
    for k, v in kw.items():
        setattr(c, k, v)
    return c


def test_remove_fillers_ru():
    out = _remove_fillers("ну вот это типа тест короче")
    assert "типа" not in out.lower()
    assert "короче" not in out.lower()
    assert "тест" in out.lower()


def test_remove_fillers_en():
    out = _remove_fillers("um so like this is basically a test")
    assert "um" not in out.lower().split()
    assert "basically" not in out.lower().split()
    assert "test" in out.lower()


def test_dedupe_repeats():
    assert _dedupe_repeats("я я я хочу") == "я хочу"
    assert _dedupe_repeats("the the cat") == "the cat"


def test_capitalize_sentences():
    out = _capitalize_sentences("привет. как дела?")
    assert out.startswith("Привет")
    assert "Как дела" in out


def test_fallback_adds_terminal_punctuation():
    out = _fallback_enhance("это простой текст")
    assert out.endswith(".")
    assert out[0].isupper()


def test_fallback_collapses_spaces():
    out = _fallback_enhance("слишком    много     пробелов")
    assert "  " not in out


def test_enhance_raw_mode_keeps_text():
    out, method = enhance("просто текст без обработки", _cfg(text_mode="raw"))
    assert method == "raw"
    assert "просто текст" in out.lower()


def test_enhance_empty():
    out, method = enhance("   ", _cfg())
    assert out == ""
    assert method == "raw"


def test_enhance_prompt_writer_fallback():
    raw = "ну типа напиши промт чтобы чат джипити сделал лендинг"
    out, method = enhance(raw, _cfg(text_mode="prompt_writer"))
    assert method == "fallback"
    assert out  # не пусто
    assert out[0].isupper()
    assert "типа" not in out.lower()


def _run_all():
    funcs = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"  ✓ {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  ✗ {fn.__name__}: {exc}")
    print(f"\nИтого: {len(funcs) - failed}/{len(funcs)} тестов прошли.")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
