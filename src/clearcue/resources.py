from __future__ import annotations

import sys
from pathlib import Path


def resource_path(name: str) -> Path:
    """Return a packaged UI asset in source and PyInstaller builds."""
    packaged_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    packaged_asset = packaged_root / "clearcue" / "assets" / name
    if packaged_asset.exists():
        return packaged_asset
    return Path(__file__).resolve().parent / "assets" / name


def bundled_model_dir(model_name: str = "tiny.en") -> Path | None:
    """Return the bundled faster-whisper model when all required files exist."""
    packaged_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    candidate = packaged_root / "models" / f"faster-whisper-{model_name}"
    required = ("config.json", "model.bin", "tokenizer.json")
    return candidate if all((candidate / filename).is_file() for filename in required) else None
