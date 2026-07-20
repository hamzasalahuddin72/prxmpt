from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_sources_are_not_stored_in_generated_build_directory() -> None:
    spec = ROOT / "scripts/prxmpt.spec"
    hook = ROOT / "scripts/hooks/hook-webrtcvad.py"
    builder = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    assert spec.is_file()
    assert hook.is_file()
    assert '"scripts\\prxmpt.spec"' in builder
    assert "build\\clearcue.spec" not in builder


def test_windows_builder_uses_project_local_pytest_temp_directory() -> None:
    builder = (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert '$PytestTemp = Join-Path $ProjectRoot "build\\pytest-temp"' in builder
    assert '"-m", "pytest", "--basetemp", $PytestTemp' in builder
    assert '"-p", "no:cacheprovider"' in builder
    assert "build/pytest-temp/" in gitignore


def test_permanent_spec_resolves_project_and_hook_paths_after_directory_move() -> None:
    spec = (ROOT / "scripts/prxmpt.spec").read_text(encoding="utf-8")
    assert "Path(SPECPATH).resolve().parent" in spec
    assert (ROOT / "scripts").resolve().parent == ROOT.resolve()
    assert 'project_root / "build" / "models"' in spec
    assert 'project_root / "scripts" / "hooks"' in spec
