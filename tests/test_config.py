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
    assert config.config_version == 2
    assert config.whisper_model == "tiny.en"
    assert config.overlay_opacity == 1.0
    assert config.speaker_id == ""
    assert config.microphone_id == ""
