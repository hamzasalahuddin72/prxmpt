from __future__ import annotations

import os
import shutil
from pathlib import Path


APP_NAME = "prxmpt"
LEGACY_APP_NAME = "ClearCue"


def _data_root() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def app_data_dir() -> Path:
    """Return a writable, per-user application data directory."""
    path = _data_root() / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def migrate_legacy_user_data() -> None:
    """Copy the previous ClearCue settings and history into prxmpt once."""
    legacy = _data_root() / LEGACY_APP_NAME
    if not legacy.is_dir():
        return
    destination = app_data_dir()
    for old_name, new_name in (
        ("settings.json", "settings.json"),
        ("clearcue.db", "prxmpt.db"),
        ("clearcue.db-wal", "prxmpt.db-wal"),
        ("clearcue.db-shm", "prxmpt.db-shm"),
    ):
        source = legacy / old_name
        target = destination / new_name
        if source.is_file() and not target.exists():
            try:
                shutil.copy2(source, target)
            except OSError:
                # Migration must never prevent the renamed application from starting.
                pass


def models_dir() -> Path:
    path = app_data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def updates_dir() -> Path:
    path = app_data_dir() / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def database_path() -> Path:
    return app_data_dir() / "prxmpt.db"
