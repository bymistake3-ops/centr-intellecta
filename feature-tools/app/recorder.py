"""Запись звука с микрофона.

Используем sounddevice: пишем поток в память (numpy), при остановке
склеиваем и при необходимости сохраняем WAV во временную папку.

Тяжёлые библиотеки (sounddevice/numpy) импортируются лениво, чтобы
текстовые тесты (--test-text) работали даже без установленного звука.
"""

from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path

from . import logger


class MicrophoneError(RuntimeError):
    """Нет доступа к микрофону или он недоступен."""


class Recorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self._frames: list = []
        self._stream = None
        self._lock = threading.Lock()
        self._recording = False
        self._start_time = 0.0

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        """Начать запись. Бросает MicrophoneError при проблемах с доступом."""
        if self._recording:
            return
        try:
            import sounddevice as sd  # ленивый импорт
        except Exception as exc:  # noqa: BLE001
            raise MicrophoneError(
                f"Не удалось загрузить звуковую библиотеку: {exc}"
            ) from exc

        self._frames = []

        def _callback(indata, frames, time_info, status):  # noqa: ANN001
            if status:
                # переполнение буфера и т.п. — не критично
                pass
            with self._lock:
                self._frames.append(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=_callback,
            )
            self._stream.start()
        except Exception as exc:  # noqa: BLE001
            raise MicrophoneError(str(exc)) from exc

        self._recording = True
        self._start_time = time.time()

    def stop(self):
        """Остановить запись и вернуть numpy-массив float32 (или None если пусто)."""
        if not self._recording:
            return None
        self._recording = False

        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None

        import numpy as np

        with self._lock:
            frames = list(self._frames)
            self._frames = []

        if not frames:
            return None

        audio = np.concatenate(frames, axis=0)
        # делаем моно одномерным массивом
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        return audio.astype(np.float32)

    def elapsed(self) -> float:
        if not self._recording:
            return 0.0
        return time.time() - self._start_time

    @staticmethod
    def save_wav(audio, sample_rate: int) -> Path | None:
        """Сохранить numpy-массив в WAV во временную папку. Вернуть путь."""
        if audio is None:
            return None
        try:
            import numpy as np
            import soundfile as sf

            tmp = Path(tempfile.gettempdir()) / "feature_tools"
            tmp.mkdir(parents=True, exist_ok=True)
            path = tmp / f"rec_{int(time.time())}.wav"
            sf.write(str(path), np.asarray(audio), sample_rate)
            return path
        except Exception as exc:  # noqa: BLE001
            logger.warn(f"Не удалось сохранить WAV (не критично): {exc}")
            return None


def list_devices() -> None:
    """Показать список звуковых устройств (для отладки)."""
    try:
        import sounddevice as sd

        print(sd.query_devices())
    except Exception as exc:  # noqa: BLE001
        logger.friendly_error(
            f"Не удалось получить список устройств: {exc}",
            "Проверьте, что установлены зависимости (./install.sh) и подключён микрофон.",
        )
