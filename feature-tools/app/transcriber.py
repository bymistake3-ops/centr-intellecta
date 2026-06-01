"""Локальная транскрибация речи через faster-whisper.

Модель загружается один раз (лениво) и переиспользуется.
Принимает либо numpy-массив float32 (16 кГц моно), либо путь к WAV.
Всё считается на этом Mac, аудио никуда не отправляется.
"""

from __future__ import annotations

from pathlib import Path

from . import logger
from .config import Config


class Transcriber:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self._model = None

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Не удалось загрузить faster-whisper: {exc}. Запустите ./install.sh"
            ) from exc

        logger.info(
            f"Загружаю модель распознавания '{self.cfg.whisper_model}' "
            "(в первый раз может скачиваться — подождите)…"
        )
        # int8 — быстро и экономно по памяти, работает и на Apple Silicon, и на Intel
        self._model = WhisperModel(
            self.cfg.whisper_model,
            device="cpu",
            compute_type="int8",
        )
        logger.ok("Модель распознавания готова.")
        return self._model

    def warmup(self) -> None:
        """Загрузить модель заранее (чтобы первая диктовка не тормозила)."""
        try:
            self._ensure_model()
        except Exception as exc:  # noqa: BLE001
            logger.warn(f"Не удалось заранее загрузить модель: {exc}")

    def transcribe(self, audio) -> tuple[str, str]:
        """Вернуть (текст, определённый_язык)."""
        model = self._ensure_model()

        language = None if self.cfg.language == "auto" else self.cfg.language
        source = str(audio) if isinstance(audio, (str, Path)) else audio

        segments, info = model.transcribe(
            source,
            language=language,
            beam_size=5,
            vad_filter=True,  # отсекаем тишину/паузы
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        detected = getattr(info, "language", language or "?")
        return text, detected
