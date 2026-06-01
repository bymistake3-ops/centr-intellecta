"""Глобальная горячая клавиша в режиме «зажми и говори» (hold-to-talk).

Используем pynput. При нажатии нужной клавиши вызываем on_press,
при отпускании — on_release. Клавиатура повторяет события нажатия,
пока клавишу держат, поэтому защищаемся флагом _held, чтобы запись
начиналась один раз.
"""

from __future__ import annotations

from . import logger

# Человеческое имя клавиши из config.yaml -> ключ pynput.
# Заполняется лениво, т.к. pynput импортируется только при запуске.
_KEY_MAP_CACHE: dict | None = None


def _build_key_map() -> dict:
    from pynput import keyboard as kb

    Key = kb.Key
    mapping = {
        "right_option": Key.alt_r,
        "left_option": Key.alt_l,
        "right_alt": Key.alt_r,
        "left_alt": Key.alt_l,
        "right_cmd": Key.cmd_r,
        "left_cmd": Key.cmd_l,
        "right_command": Key.cmd_r,
        "left_command": Key.cmd_l,
        "right_ctrl": Key.ctrl_r,
        "left_ctrl": Key.ctrl_l,
        "right_control": Key.ctrl_r,
        "fn": getattr(Key, "fn", None),
    }
    # Функциональные клавиши F13..F20 (F18 удобна для маппинга на Karabiner и т.п.)
    for n in range(1, 21):
        fk = getattr(Key, f"f{n}", None)
        if fk is not None:
            mapping[f"f{n}"] = fk
    return {k: v for k, v in mapping.items() if v is not None}


def resolve_key(name: str):
    """Вернуть объект клавиши pynput по человеческому имени."""
    global _KEY_MAP_CACHE
    if _KEY_MAP_CACHE is None:
        _KEY_MAP_CACHE = _build_key_map()
    return _KEY_MAP_CACHE.get(name.strip().lower())


class HotkeyListener:
    """Слушает одну клавишу в режиме удержания."""

    def __init__(self, hotkey_name: str, on_press, on_release) -> None:
        self.hotkey_name = hotkey_name
        self._on_press_cb = on_press
        self._on_release_cb = on_release
        self._target = None
        self._held = False
        self._listener = None

    def _press(self, key) -> None:
        if key == self._target and not self._held:
            self._held = True
            try:
                self._on_press_cb()
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Ошибка при старте записи: {exc}")

    def _release(self, key) -> None:
        if key == self._target and self._held:
            self._held = False
            try:
                self._on_release_cb()
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Ошибка при остановке записи: {exc}")

    def start(self) -> bool:
        """Запустить слушатель. Вернуть True при успехе."""
        self._target = resolve_key(self.hotkey_name)
        if self._target is None:
            logger.friendly_error(
                f"Горячая клавиша '{self.hotkey_name}' не распознана.",
                "Откройте config.yaml и укажите, например, right_option, f18 или left_option.",
            )
            return False

        try:
            from pynput import keyboard as kb
        except Exception as exc:  # noqa: BLE001
            logger.friendly_error(
                f"Не удалось загрузить отслеживание клавиатуры: {exc}",
                "Запустите ./install.sh ещё раз.",
            )
            return False

        self._listener = kb.Listener(on_press=self._press, on_release=self._release)
        self._listener.start()
        return True

    def join(self) -> None:
        if self._listener is not None:
            self._listener.join()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
