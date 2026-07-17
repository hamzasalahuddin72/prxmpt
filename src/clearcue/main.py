from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from clearcue.config import ConfigStore
from clearcue.paths import logs_dir, migrate_legacy_user_data
from clearcue.resources import resource_path
from clearcue.services.global_hotkeys import GlobalHotkeys
from clearcue.storage.database import Database
from clearcue.ui.main_window import MainWindow
from clearcue.ui.skins import activate_skin
from clearcue.ui.theme import stylesheet_for_skin


LOGGER = logging.getLogger(__name__)


def _configure_logging() -> None:
    handler = RotatingFileHandler(
        logs_dir() / "prxmpt.log",
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

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HamzaSalahuddin.prxmpt.1")
    except Exception:
        pass


def main() -> int:
    migrate_legacy_user_data()
    _set_windows_identity()
    _configure_logging()
    _install_exception_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("prxmpt")
    app.setApplicationDisplayName("prxmpt")
    app.setOrganizationName("Hamza Salahuddin")
    app.setWindowIcon(QIcon(str(resource_path("prxmpt.ico"))))
    app.setQuitOnLastWindowClosed(False)
    config_store = ConfigStore()
    config = config_store.load()
    activate_skin(config.skin_id)
    app.setStyleSheet(stylesheet_for_skin(config.skin_id))
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
