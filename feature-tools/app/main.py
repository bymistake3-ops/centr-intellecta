"""Фича Инструменты — точка входа.

Режимы запуска:
  python app/main.py                # обычный режим (горячая клавиша)
  python app/main.py --test-text    # проверка улучшателя на примере (без микрофона)
  python app/main.py --record-once   # один раз записать по Enter (без горячей клавиши)
  python app/main.py --list-devices  # показать звуковые устройства
"""

from __future__ import annotations

import argparse
import sys
import threading
import time

from . import history, logger
from .config import Config, load_config
from .text_enhancer import check_ollama, enhance

# Пример сырой фразы для --test-text
DEMO_PHRASE = (
    "слушай напиши мне промт ну типа чтобы чат джипити помог мне сделать "
    "лендинг для моего продукта и чтобы там было красиво понятно и с "
    "нормальной структурой"
)


def _print_config(cfg: Config) -> None:
    logger.info(f"Горячая клавиша: {cfg.hotkey}")
    logger.info(f"Язык: {cfg.language} | Модель: {cfg.whisper_model} | Режим текста: {cfg.text_mode}")
    logger.info(f"Вставка: {cfg.paste_mode} | Ollama: {'вкл' if cfg.use_ollama else 'выкл'} ({cfg.ollama_model})")
    for w in cfg.warnings:
        logger.warn(w)


def _deliver(cfg: Config, raw: str, improved: str, method: str, language: str) -> None:
    """Показать результат, скопировать в буфер, по желанию вставить."""
    from . import clipboard, paste

    logger.block("Черновая транскрибация:", raw)
    logger.block("Улучшенный текст:", improved, color="\033[32m")
    logger.info(f"Способ обработки: {method} | язык: {language}")

    copied = clipboard.copy(improved)
    if copied:
        logger.ok("Скопировано в буфер обмена.")
    else:
        logger.warn("Не удалось скопировать в буфер обмена.")

    pasted = False
    if cfg.paste_mode in ("auto_paste", "both"):
        # небольшая пауза, чтобы фокус вернулся в активное поле
        time.sleep(0.25)
        pasted = paste.paste_into_active_field()
        if pasted:
            logger.ok("Текст вставлен в активное поле.")
        else:
            logger.warn("Текст скопирован в буфер обмена. Вставьте его вручную: Cmd+V.")

    if cfg.show_notifications:
        paste.notify("Текст готов и в буфере обмена.")

    if cfg.save_history:
        history.append(raw, improved, method, language, cfg.history_limit)

    status = "вставлен" if pasted else ("в буфере" if copied else "ошибка")
    logger.info(f"Статус вставки: {status}")


# ---------------------------------------------------------------------------
# Режим --test-text
# ---------------------------------------------------------------------------
def run_test_text(cfg: Config) -> int:
    logger.title("Тест улучшателя текста (без микрофона)")
    _print_config(cfg)
    if cfg.use_ollama:
        if check_ollama(cfg):
            logger.ok("Ollama доступна — текст улучшит нейросеть.")
        else:
            logger.warn("Ollama недоступна — сработает простая встроенная очистка (fallback).")

    logger.block("Пример сырой фразы:", DEMO_PHRASE)
    improved, method = enhance(DEMO_PHRASE, cfg)
    logger.block("Результат:", improved, color="\033[32m")
    logger.info(f"Способ обработки: {method}")
    return 0


# ---------------------------------------------------------------------------
# Режим --record-once
# ---------------------------------------------------------------------------
def run_record_once(cfg: Config) -> int:
    from .recorder import MicrophoneError, Recorder
    from .transcriber import Transcriber

    logger.title("Разовая запись (без горячей клавиши)")
    _print_config(cfg)

    rec = Recorder(sample_rate=cfg.sample_rate)
    input("Нажмите Enter, чтобы НАЧАТЬ запись… ")
    try:
        rec.start()
    except MicrophoneError as exc:
        logger.friendly_error(
            f"Нет доступа к микрофону ({exc}).",
            "Откройте System Settings → Privacy & Security → Microphone и "
            "включите доступ для Terminal, затем перезапустите.",
        )
        return 1

    logger.ok("Recording… говорите. Нажмите Enter, чтобы остановить.")
    input()
    audio = rec.stop()

    if audio is None or len(audio) == 0:
        logger.warn("Ничего не записалось. Попробуйте ещё раз.")
        return 1

    duration = len(audio) / cfg.sample_rate
    logger.info(f"Записано {duration:.1f} сек. Распознаю…")

    Recorder.save_wav(audio, cfg.sample_rate)
    transcriber = Transcriber(cfg)
    raw, language = transcriber.transcribe(audio)
    if not raw.strip():
        logger.warn("Речь не распознана. Говорите чуть громче/ближе к микрофону.")
        return 1

    improved, method = enhance(raw, cfg)
    _deliver(cfg, raw, improved, method, language)
    return 0


# ---------------------------------------------------------------------------
# Обычный режим: горячая клавиша
# ---------------------------------------------------------------------------
class HotkeyApp:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        from .recorder import Recorder
        from .transcriber import Transcriber

        self.recorder = Recorder(sample_rate=cfg.sample_rate)
        self.transcriber = Transcriber(cfg)
        self._busy = False  # идёт обработка предыдущей записи
        self._max_timer: threading.Timer | None = None

    def on_press(self) -> None:
        from .recorder import MicrophoneError
        from . import paste

        if self.recorder.is_recording or self._busy:
            return
        try:
            self.recorder.start()
        except MicrophoneError as exc:
            logger.friendly_error(
                f"Нет доступа к микрофону ({exc}).",
                "System Settings → Privacy & Security → Microphone → включите Terminal.",
            )
            return
        logger.info("Recording… говорите (отпустите клавишу, чтобы закончить)")
        if self.cfg.play_sounds:
            paste.play_sound("Tink")
        # авто-стоп по максимальной длительности
        self._max_timer = threading.Timer(self.cfg.max_record_seconds, self._auto_stop)
        self._max_timer.daemon = True
        self._max_timer.start()

    def _auto_stop(self) -> None:
        if self.recorder.is_recording:
            logger.warn("Достигнут лимит длительности — останавливаю запись.")
            self.on_release()

    def on_release(self) -> None:
        if not self.recorder.is_recording:
            return
        if self._max_timer is not None:
            self._max_timer.cancel()
            self._max_timer = None

        audio = self.recorder.stop()
        from . import paste

        if self.cfg.play_sounds:
            paste.play_sound("Pop")

        if audio is None or len(audio) == 0:
            logger.warn("Запись пустая — пропускаю.")
            return

        duration = len(audio) / self.cfg.sample_rate
        if duration < self.cfg.min_record_seconds:
            logger.warn(f"Слишком короткая запись ({duration:.2f} сек) — пропускаю.")
            return

        # обработку делаем в отдельном потоке, чтобы не блокировать слушатель клавиш
        self._busy = True
        threading.Thread(target=self._process, args=(audio, duration), daemon=True).start()

    def _process(self, audio, duration: float) -> None:
        try:
            from .recorder import Recorder

            logger.info(f"Записано {duration:.1f} сек. Распознаю…")
            Recorder.save_wav(audio, self.cfg.sample_rate)
            raw, language = self.transcriber.transcribe(audio)
            if not raw.strip():
                logger.warn("Речь не распознана. Попробуйте ещё раз ближе к микрофону.")
                return
            improved, method = enhance(raw, self.cfg)
            _deliver(self.cfg, raw, improved, method, language)
        except Exception as exc:  # noqa: BLE001
            logger.friendly_error(
                f"Сбой при обработке записи: {exc}",
                "Проверьте, что установлены зависимости (./install.sh).",
            )
        finally:
            self._busy = False
            logger.info("Готов к следующей диктовке. Зажмите горячую клавишу.")


def run_hotkey_mode(cfg: Config) -> int:
    from .hotkey import HotkeyListener

    logger.title("Фича Инструменты запущен. Зажмите горячую клавишу и говорите.")
    _print_config(cfg)

    if cfg.use_ollama:
        if check_ollama(cfg):
            logger.ok("Ollama доступна — текст улучшит нейросеть.")
        else:
            logger.warn(
                "Ollama недоступна — текст обработает простая встроенная очистка. "
                "Чтобы включить нейросеть: установите Ollama и выполните "
                f"'ollama pull {cfg.ollama_model}'."
            )

    app = HotkeyApp(cfg)
    # прогреваем модель заранее, чтобы первая диктовка не ждала загрузку
    app.transcriber.warmup()

    listener = HotkeyListener(cfg.hotkey, app.on_press, app.on_release)
    if not listener.start():
        return 1

    logger.ok(f"Слушаю клавишу '{cfg.hotkey}'. Нажмите Ctrl+C для выхода.")
    logger.warn(
        "Если запись не стартует по клавише — дайте доступ к мониторингу клавиатуры: "
        "System Settings → Privacy & Security → Accessibility и Input Monitoring → "
        "включите ваш терминал."
    )
    try:
        listener.join()
    except KeyboardInterrupt:
        logger.info("Выход. Пока!")
        listener.stop()
    return 0


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="feature-tools",
        description="Фича Инструменты — локальный голосовой диктовщик для macOS.",
    )
    parser.add_argument("--test-text", action="store_true",
                        help="Проверить улучшатель текста на примере (без микрофона).")
    parser.add_argument("--record-once", action="store_true",
                        help="Записать один раз по Enter (без горячей клавиши).")
    parser.add_argument("--list-devices", action="store_true",
                        help="Показать звуковые устройства.")
    parser.add_argument("--config", default=None, help="Путь к config.yaml.")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)

    if args.list_devices:
        from .recorder import list_devices

        list_devices()
        return 0
    if args.test_text:
        return run_test_text(cfg)
    if args.record_once:
        return run_record_once(cfg)
    return run_hotkey_mode(cfg)


if __name__ == "__main__":
    sys.exit(main())
