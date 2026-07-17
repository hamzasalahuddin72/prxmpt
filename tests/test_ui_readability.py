from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_scaled_popup_labels_do_not_use_clipping_graphics_effects() -> None:
    main_window = (ROOT / "src/clearcue/ui/main_window.py").read_text(encoding="utf-8")
    popup_cluster = (ROOT / "src/clearcue/ui/popup_cluster.py").read_text(
        encoding="utf-8"
    )
    assert "QGraphicsDropShadowEffect" not in main_window
    assert "class ReadableLabel(QLabel)" in popup_cluster
    for name in ("LiveLabel", "AutoAnswerLabel", "StealthLabel"):
        assert f'"{name}"' in popup_cluster


def test_model_badge_uses_a_valid_bold_font_call() -> None:
    controls = (ROOT / "src/clearcue/ui/glass_controls.py").read_text(
        encoding="utf-8"
    )
    assert "font.setBold(True)" in controls
    assert "font.setWeight(600)" not in controls


def test_model_badge_opens_validated_model_dropdown() -> None:
    main_window = (ROOT / "src/clearcue/ui/main_window.py").read_text(
        encoding="utf-8"
    )
    assert "self.model_badge.clicked.connect(self._show_model_menu)" in main_window
    assert "discover_available_models" in main_window
    assert "self._select_answer_model" in main_window


def test_logo_replaces_eye_toggle_and_audio_levels_drive_lamps() -> None:
    main_window = (ROOT / "src/clearcue/ui/main_window.py").read_text(
        encoding="utf-8"
    )
    controls = (ROOT / "src/clearcue/ui/glass_controls.py").read_text(
        encoding="utf-8"
    )
    assert "self.brand.clicked.connect(self._toggle_controls)" in main_window
    assert "collapse_button" not in main_window
    assert "lamp.setLevel(value)" in main_window
    assert "class LogoToggleButton(TactileIconButton)" in controls
    assert "class AudioLevelLamp(QWidget)" in controls
    assert "48 if target >= self._display_level else 155" in controls
