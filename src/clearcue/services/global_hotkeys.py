from __future__ import annotations

from collections.abc import Callable


class GlobalHotkeys:
    """Register only the documented shortcuts; no general keystrokes are retained."""

    def __init__(
        self,
        on_toggle_session: Callable[[], None],
        on_generate: Callable[[], None],
        on_toggle_overlay: Callable[[], None],
    ) -> None:
        self.on_toggle_session = on_toggle_session
        self.on_generate = on_generate
        self.on_toggle_overlay = on_toggle_overlay
        self._listener = None

    def start(self) -> None:
        try:
            from pynput import keyboard

            self._listener = keyboard.GlobalHotKeys(
                {
                    "<ctrl>+<alt>+s": self.on_toggle_session,
                    "<ctrl>+<alt>+a": self.on_generate,
                    "<ctrl>+<alt>+o": self.on_toggle_overlay,
                }
            )
            self._listener.start()
        except Exception:
            self._listener = None

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            finally:
                self._listener = None

