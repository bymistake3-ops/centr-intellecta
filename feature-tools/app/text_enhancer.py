"""Улучшение чернового текста.

Два пути:
1. Если доступна Ollama (локальная нейросеть) — отправляем текст
   ей вместе с системным промтом под выбранный режим.
2. Если Ollama недоступна — простой встроенный fallback:
   чистим пробелы, убираем слова-паразиты и повторы,
   ставим заглавную букву и точку.

Никакие данные наружу не уходят: Ollama работает на этом же Mac
(localhost). Платные облачные API не используются.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from . import logger
from .config import Config

# ---------------------------------------------------------------------------
# Слова-паразиты (мусор), которые fallback убирает как отдельные слова.
# ---------------------------------------------------------------------------
_FILLERS_RU = {
    "э", "эм", "ээ", "ммм", "мм", "нуу", "ну", "вот", "типа", "блин",
    "короче", "значит", "как бы", "это самое", "в общем", "так сказать",
    "то есть", "слушай", "слышишь",
}
_FILLERS_EN = {
    "uh", "um", "umm", "uhh", "er", "err", "like", "you know", "i mean",
    "kinda", "sorta", "basically", "literally", "actually", "well",
}
# Многословные паразиты убираем отдельной регуляркой
_FILLER_PHRASES = sorted(
    {p for p in (_FILLERS_RU | _FILLERS_EN) if " " in p},
    key=len,
    reverse=True,
)
_FILLER_WORDS = {p for p in (_FILLERS_RU | _FILLERS_EN) if " " not in p}


def check_ollama(cfg: Config, timeout: float = 1.5) -> bool:
    """Проверить, отвечает ли локальная Ollama и есть ли нужная модель."""
    if not cfg.use_ollama:
        return False
    try:
        req = urllib.request.Request(f"{cfg.ollama_url}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return False

    models = {m.get("name", "") for m in data.get("models", [])}
    # Имя может быть с тегом (qwen2.5:7b) или без — проверяем по префиксу
    wanted = cfg.ollama_model
    base = wanted.split(":")[0]
    return any(m == wanted or m.split(":")[0] == base for m in models)


def enhance(text: str, cfg: Config) -> tuple[str, str]:
    """Вернуть (улучшенный_текст, способ).

    способ: "ollama", "fallback" или "raw".
    """
    text = (text or "").strip()
    if not text:
        return "", "raw"

    if cfg.text_mode == "raw":
        return _basic_cleanup(text), "raw"

    system_prompt = cfg.prompt_text()
    if cfg.use_ollama and system_prompt and check_ollama(cfg):
        try:
            improved = _enhance_with_ollama(text, system_prompt, cfg)
            if improved.strip():
                return improved.strip(), "ollama"
            logger.warn("Ollama вернула пустой ответ — использую простую очистку.")
        except Exception as exc:  # noqa: BLE001
            logger.warn(f"Ollama не ответила ({exc}) — использую простую очистку.")

    return _fallback_enhance(text), "fallback"


# ---------------------------------------------------------------------------
# Путь 1: Ollama
# ---------------------------------------------------------------------------
def _enhance_with_ollama(text: str, system_prompt: str, cfg: Config) -> str:
    payload = {
        "model": cfg.ollama_model,
        "system": system_prompt,
        "prompt": text,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{cfg.ollama_url}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # Генерация может занять время — даём щедрый таймаут
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("response", "")


# ---------------------------------------------------------------------------
# Путь 2: Fallback (без нейросети)
# ---------------------------------------------------------------------------
def _basic_cleanup(text: str) -> str:
    """Минимальная косметика: пробелы и переносы."""
    text = text.replace("\r\n", "\n")
    # схлопываем повторяющиеся пробелы
    text = re.sub(r"[ \t]+", " ", text)
    # пробелы перед знаками препинания
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    # не больше двух переносов подряд
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _remove_fillers(text: str) -> str:
    # сначала многословные паразиты
    for phrase in _FILLER_PHRASES:
        text = re.sub(rf"(?<!\w){re.escape(phrase)}(?!\w)", "", text, flags=re.IGNORECASE)

    # затем одиночные слова
    def _keep(token: str) -> bool:
        stripped = token.strip(".,!?;:—-()\"'»«").lower()
        return stripped not in _FILLER_WORDS

    tokens = text.split()
    tokens = [t for t in tokens if _keep(t)]
    return " ".join(tokens)


def _dedupe_repeats(text: str) -> str:
    """Убрать подряд идущие повторы одного слова: 'я я я' -> 'я'."""
    return re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", text, flags=re.IGNORECASE)


def _capitalize_sentences(text: str) -> str:
    """Сделать первую букву каждого предложения заглавной."""
    def _cap(match: re.Match) -> str:
        return match.group(0).upper()

    text = re.sub(r"(^\s*[a-zа-яё])", _cap, text)
    text = re.sub(r"([.!?]\s+)([a-zа-яё])",
                  lambda m: m.group(1) + m.group(2).upper(), text)
    return text


def _fallback_enhance(text: str) -> str:
    text = _basic_cleanup(text)
    text = _remove_fillers(text)
    text = _dedupe_repeats(text)
    text = _basic_cleanup(text)  # ещё раз подчистить пробелы после удалений
    text = _capitalize_sentences(text)
    text = text.strip()
    # если в конце нет знака завершения — поставить точку
    if text and text[-1] not in ".!?…:":
        text += "."
    return text
