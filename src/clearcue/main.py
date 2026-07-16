from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler

from PySide6.QtWidgets import QApplication

from clearcue.config import ConfigStore
from clearcue.paths import logs_dir
from clearcue.services.global_hotkeys import GlobalHotkeys
from clearcue.storage.database import Database
from clearcue.ui.main_window import MainWindow
from clearcue.ui.theme import APP_STYLESHEET


LOGGER = logging.getLogger(__name__)


def _configure_logging() -> None:
    handler = RotatingFileHandler(
        logs_dir() / "clearcue.log",
        maxBytes=500_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def _install_exception_logging() -> None:
    def unhandled(exception_type, exception, traceback) -> None:
        LOGGER.critical(
            "Unhandled application exception",
            exc_info=(exception_type, exception, traceback),
        )

    def unhandled_thread(args: threading.ExceptHookArgs) -> None:
        LOGGER.critical(
            "Unhandled worker exception in %s",
            args.thread.name if args.thread else "unknown thread",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = unhandled
    threading.excepthook = unhandled_thread


def _set_windows_identity() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HamzaSalahuddin.ClearCue.1")
    except Exception:
        pass


def main() -> int:
    _set_windows_identity()
    _configure_logging()
    _install_exception_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("ClearCue")
    app.setApplicationDisplayName("ClearCue Interview Coach")
    app.setOrganizationName("Hamza Salahuddin")
    app.setStyleSheet(APP_STYLESHEET)

    config_store = ConfigStore()
    config = config_store.load()
    database = Database()
    window = MainWindow(database, config_store, config)
    window.show()

    hotkeys = GlobalHotkeys(
        window.hotkey_bridge.toggle_session.emit,
        window.hotkey_bridge.generate.emit,
        window.hotkey_bridge.toggle_overlay.emit,
    )
    hotkeys.start()
    app.aboutToQuit.connect(hotkeys.stop)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
