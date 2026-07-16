from pathlib import Path

from clearcue.config import AppConfig, ConfigStore


def test_config_round_trip(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "settings.json")
    expected = AppConfig(answer_provider="ollama", overlay_opacity=0.72, auto_generate=False)
    store.save(expected)
    actual = store.load()
    assert actual.answer_provider == "ollama"
    assert actual.overlay_opacity == 0.72
    assert actual.auto_generate is False


def test_invalid_config_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")
    assert ConfigStore(path).load() == AppConfig()


def test_legacy_config_migrates_to_performance_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"whisper_model": "small.en", "overlay_opacity": 0.72, '
        '"speaker_id": "stale-output", "microphone_id": "stale-mic"}',
        encoding="utf-8",
    )
    config = ConfigStore(path).load()
    assert config.config_version == 4
    assert config.whisper_model == "tiny.en"
    assert config.overlay_opacity == 1.0
    assert config.speaker_id == ""
    assert config.microphone_id == ""


def test_v2_config_migrates_microphone_and_gpu_without_resetting_loopback(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"config_version": 2, "speaker_id": "working-loopback", '
        '"microphone_id": "old-wasapi-id", "whisper_device": "cuda", '
        '"whisper_compute_type": "float16"}',
        encoding="utf-8",
    )
    config = ConfigStore(path).load()
    assert config.config_version == 4
    assert config.speaker_id == "working-loopback"
    assert config.microphone_id == ""
    assert config.whisper_device == "cpu"
    assert config.whisper_compute_type == "int8"
    assert config.auto_check_updates is True


def test_v3_config_migrates_to_popup_audio_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"config_version": 3, "speaker_enabled": false, '
        '"microphone_enabled": false, "popup_width": 410}',
        encoding="utf-8",
    )
    config = ConfigStore(path).load()
    assert config.config_version == 4
    assert config.speaker_enabled is True
    assert config.microphone_enabled is True
    assert config.popup_width == 520
    assert config.popup_height == 760
    assert config.popup_drag_locked is True
