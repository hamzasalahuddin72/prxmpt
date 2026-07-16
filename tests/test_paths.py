from clearcue.paths import migrate_legacy_user_data


def test_legacy_clearcue_data_is_copied_without_deleting_source(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("clearcue.paths._data_root", lambda: tmp_path)
    legacy = tmp_path / "ClearCue"
    legacy.mkdir()
    (legacy / "settings.json").write_text('{"config_version": 4}', encoding="utf-8")
    (legacy / "clearcue.db").write_bytes(b"sqlite-history")

    migrate_legacy_user_data()

    current = tmp_path / "prxmpt"
    assert (current / "settings.json").read_text(encoding="utf-8") == '{"config_version": 4}'
    assert (current / "prxmpt.db").read_bytes() == b"sqlite-history"
    assert (legacy / "clearcue.db").is_file()
