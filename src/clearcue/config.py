from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from clearcue.paths import settings_path


CURRENT_CONFIG_VERSION = 9
VALID_SKIN_IDS = frozenset({"midnight", "azure_knight", "rose_quartz"})


@dataclass(slots=True)
class AppConfig:
    config_version: int = CURRENT_CONFIG_VERSION
    speaker_id: str = ""
    microphone_id: str = ""
    speaker_enabled: bool = True
    microphone_enabled: bool = True
    sample_rate: int = 48_000
    whisper_model: str = "tiny.en"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    answer_provider: str = "local"
    gemini_model: str = "gemini-3.5-flash"
    openai_model: str = "gpt-5.6-luna"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"
    answer_style: str = "concise"
    auto_generate: bool = True
    overlay_opacity: float = 1.0
    overlay_width: int = 620
    overlay_height: int = 430
    consent_acknowledged: bool = False
    save_transcripts: bool = True
    auto_check_updates: bool = True
    popup_width: int = 720
    popup_height: int = 366
    popup_drag_locked: bool = True
    skin_id: str = "midnight"


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings_path()

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            allowed = {field.name for field in fields(AppConfig)}
            values = {key: value for key, value in raw.items() if key in allowed}
            config = AppConfig(**values)
            source_version = int(raw.get("config_version", 1))
            if source_version < 2:
                # v1.0.5 is a performance-first release. Existing installations
                # used small.en by default, so migrate that default to tiny.en.
                if config.whisper_model == "small.en":
                    config.whisper_model = "tiny.en"
                # Saved WASAPI identifiers can become invalid after reconnecting
                # a headset, rebooting, or changing VoiceMeeter routes. Start the
                # reliability release from the live Windows defaults.
                config.speaker_id = ""
                config.microphone_id = ""
                config.overlay_opacity = 1.0
            if source_version < 3:
                # v1.0.6 changes microphone IDs from WASAPI endpoint strings to
                # PortAudio indices. Re-select the live Windows default and use
                # the reliable CPU path until CUDA is explicitly chosen again.
                config.microphone_id = ""
                config.whisper_device = "cpu"
                config.whisper_compute_type = "int8"
                config.auto_check_updates = True
            if source_version < 4:
                # v1.0.7 replaces the dashboard/overlay pair with one compact
                # popup. Both audio sources remain enabled until the user
                # switches either one off from the popup controls.
                config.speaker_enabled = True
                config.microphone_enabled = True
                config.popup_width = 520
                config.popup_height = 760
                config.popup_drag_locked = True
            if source_version < 5:
                # v1.0.8 adopts the approved 551x827 prxmpt reference canvas.
                config.whisper_model = "tiny.en"
                config.whisper_device = "cpu"
                config.whisper_compute_type = "int8"
                config.popup_width = 551
                config.popup_height = 827
            if source_version < 6:
                # v1.0.11 adds Gemini without changing an existing user's
                # selected provider. The API key remains outside this file in
                # Windows Credential Manager.
                config.gemini_model = "gemini-3.5-flash"
            if source_version < 7:
                # v1.0.15 keeps the approved 720 px horizontal four-surface
                # popup cluster introduced by the prior UI migration.
                config.popup_width = 720
                config.popup_height = 366
            if source_version < 8:
                # v1.0.16 introduces optional popup skins. Existing users keep
                # the exact Midnight palette unless they choose another skin.
                config.skin_id = "midnight"
            if source_version < 9 and config.skin_id == "azure_knight":
                # v1.0.17 makes Azure Knight fully opaque. Reset the separate
                # window-opacity preference once so an older saved slider value
                # cannot keep the upgraded skin translucent.
                config.overlay_opacity = 1.0
            config.config_version = CURRENT_CONFIG_VERSION
            if config.answer_provider not in {"local", "gemini", "openai", "ollama"}:
                config.answer_provider = "local"
            config.overlay_opacity = min(1.0, max(0.45, config.overlay_opacity))
            config.popup_width = min(720, max(480, int(config.popup_width)))
            config.popup_height = min(366, max(244, int(config.popup_height)))
            if config.skin_id not in VALID_SKIN_IDS:
                config.skin_id = "midnight"
            return config
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
        temporary.replace(self.path)
