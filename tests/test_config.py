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
    assert config.config_version == 9
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
    assert config.config_version == 9
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
    assert config.config_version == 9
    assert config.speaker_enabled is True
    assert config.microphone_enabled is True
    assert config.popup_width == 720
    assert config.popup_height == 366
    assert config.popup_drag_locked is True


def test_v4_config_adopts_bundled_model_and_final_reference_size(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"config_version": 4, "whisper_model": "base.en", '
        '"whisper_device": "cuda", "popup_width": 520, "popup_height": 760}',
        encoding="utf-8",
    )
    config = ConfigStore(path).load()
    assert config.config_version == 9
    assert config.whisper_model == "tiny.en"
    assert config.whisper_device == "cpu"
    assert config.whisper_compute_type == "int8"
    assert (config.popup_width, config.popup_height) == (720, 366)


def test_v5_config_adds_gemini_without_changing_provider(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"config_version": 5, "answer_provider": "ollama", '
        '"ollama_model": "qwen3:8b"}',
        encoding="utf-8",
    )
    config = ConfigStore(path).load()
    assert config.config_version == 9
    assert config.answer_provider == "ollama"
    assert config.gemini_model == "gemini-3.5-flash"


def test_unknown_answer_provider_falls_back_to_local(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"config_version": 6, "answer_provider": "removed-provider"}',
        encoding="utf-8",
    )
    assert ConfigStore(path).load().answer_provider == "local"


def test_v6_config_adopts_horizontal_popup_reference_size(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"config_version": 6, "popup_width": 551, "popup_height": 827}',
        encoding="utf-8",
    )
    config = ConfigStore(path).load()
    assert config.config_version == 9
    assert (config.popup_width, config.popup_height) == (720, 366)


def test_v7_config_keeps_existing_users_on_midnight_skin(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"config_version": 7}', encoding="utf-8")
    config = ConfigStore(path).load()
    assert config.config_version == 9
    assert config.skin_id == "midnight"


def test_unknown_skin_falls_back_to_midnight(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"config_version": 8, "skin_id": "missing_skin"}',
        encoding="utf-8",
    )
    assert ConfigStore(path).load().skin_id == "midnight"


def test_v8_azure_knight_migrates_to_full_window_opacity(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"config_version": 8, "skin_id": "azure_knight", '
        '"overlay_opacity": 0.55}',
        encoding="utf-8",
    )
    config = ConfigStore(path).load()
    assert config.config_version == 9
    assert config.skin_id == "azure_knight"
    assert config.overlay_opacity == 1.0


def test_rose_quartz_skin_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"config_version": 9, "skin_id": "rose_quartz"}',
        encoding="utf-8",
    )
    assert ConfigStore(path).load().skin_id == "rose_quartz"
