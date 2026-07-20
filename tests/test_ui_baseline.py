from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.24"


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_ui_baseline_is_explicit_and_authoritative() -> None:
    baseline = _read("docs/UI_BASELINE.md")
    readme = _read("README.md")
    assert f"authoritative from version {VERSION}" in baseline
    assert "720 × 58" in baseline
    assert "720 × 35" in baseline
    assert "720 × 261" in baseline
    assert "720 × 164" in baseline
    assert "docs/UI_BASELINE.md" in readme


def test_latest_three_changes_are_locked_into_the_baseline() -> None:
    baseline = _read("docs/UI_BASELINE.md")
    controls = _read("src/clearcue/ui/glass_controls.py")
    builder = _read("scripts/build_windows.ps1")
    assert "64% opacity" in baseline
    assert "target = 0.64 if dimmed else 1.0" in controls
    assert "painter.setOpacity(0.11 * self._hover_progress)" in controls
    assert '$PytestTemp = Join-Path $ProjectRoot "build\\pytest-temp"' in builder
    assert '"-m", "pytest", "--basetemp", $PytestTemp' in builder


def test_approved_ten_pixel_popup_corners_are_locked_into_the_baseline() -> None:
    baseline = _read("docs/UI_BASELINE.md")
    theme = _read("src/clearcue/ui/theme.py")
    helpers = _read("src/clearcue/ui/popup_helpers.py")
    cluster = _read("src/clearcue/ui/popup_cluster.py")
    controls = _read("src/clearcue/ui/glass_controls.py")
    assert "10 logical px corner radius" in baseline
    assert "POPUP_CORNER_RADIUS = 10" in helpers
    assert theme.count("border-radius: 10px;") == 3
    assert "border-radius: 15px;" not in theme
    assert "22.6793" not in cluster
    assert "22.6793" not in controls
    assert cluster.count("POPUP_CORNER_RADIUS") >= 5
    assert controls.count("POPUP_CORNER_RADIUS") >= 3


def test_active_version_metadata_matches_the_baseline_release() -> None:
    assert f'version = "{VERSION}"' in _read("pyproject.toml")
    assert f'__version__ = "{VERSION}"' in _read("src/clearcue/__init__.py")
    assert f'#define MyAppVersion "{VERSION}"' in _read("installer/prxmpt.iss")
    assert f"prxmptUpdate_{VERSION}.exe" in _read("scripts/build_windows.ps1")
    assert f"prxmptUpdate_{VERSION}.exe" in _read(".github/workflows/build-windows.yml")
    assert f"PATCH_NOTES_{VERSION}.md" in _read("installer/prxmpt.iss")
    versioned_builders = {path.name for path in ROOT.glob("BUILD_UPDATE_*.bat")}
    assert f"BUILD_UPDATE_V{VERSION}.bat" in versioned_builders


def test_current_guides_do_not_restore_removed_top_bar_shortcuts() -> None:
    installation = _read("README_INSTALLATION.md").lower()
    designer = _read("src/clearcue/assets/prxmpt-top-bar.ui")
    main_window = _read("src/clearcue/ui/main_window.py")
    assert "click the eye button" not in installation
    assert "ProfileButton" not in designer
    assert "collapse_button" not in main_window
    assert "self.brand.clicked.connect(self._toggle_controls)" in main_window
    for dormant_asset in ("profile.png", "collapse.png"):
        assert dormant_asset not in designer
        assert dormant_asset not in main_window
