import hashlib
import json
import sys
import xml.etree.ElementTree as ET

from clearcue.resources import bundled_model_dir, resource_path


def test_approved_svg_assets_are_byte_exact() -> None:
    manifest_path = resource_path("asset_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest) == 20
    for filename, expected in manifest.items():
        actual = hashlib.sha256(resource_path(filename).read_bytes()).hexdigest()
        assert actual == expected, filename


def test_designer_forms_reference_the_canonical_visible_assets() -> None:
    expected = {
        "answer-button.png",
        "answer-navigation.png",
        "clear-button.png",
        "drag-lock.png",
        "exit.png",
        "ghost-writer-button.png",
        "history-toggle-button.png",
        "microphone.png",
        "opacity-button.png",
        "prxmpt-logo.png",
        "settings.png",
        "speaker.png",
    }
    referenced: set[str] = set()
    for filename in (
        "prxmpt-top-bar.ui",
        "prxmpt-prompt-screen.ui",
        "prxmpt-feedback-window.ui",
    ):
        root = ET.parse(resource_path(filename)).getroot()
        for element in root.iter():
            if element.text and element.text.strip().endswith(".png"):
                referenced.add(element.text.strip())
    assert expected <= referenced


def test_supplied_popup_svgs_are_preserved_byte_exact() -> None:
    manifest = json.loads(
        resource_path("popup_svg_manifest.json").read_text(encoding="utf-8")
    )
    for filename, expected in manifest.items():
        assert hashlib.sha256(resource_path(filename).read_bytes()).hexdigest() == expected


def test_supplied_popup_svgs_keep_the_new_reference_canvases() -> None:
    expected = {
        "prxmpt-top-bar.svg": (720, 58),
        "prxmpt-prompt-screen.svg": (720, 35),
        "prxmpt-feedback-window.svg": (720, 261),
        "prxmpt-feedback-loading.svg": (720, 261),
        "prxmpt-history-popup.svg": (720, 164),
        "prxmpt-prompt-live.svg": (720, 35),
    }
    for filename, size in expected.items():
        root = ET.parse(resource_path(filename)).getroot()
        assert (int(root.attrib["width"]), int(root.attrib["height"])) == size


def test_bundled_model_requires_complete_local_snapshot(monkeypatch, tmp_path) -> None:
    model = tmp_path / "models" / "faster-whisper-tiny.en"
    model.mkdir(parents=True)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert bundled_model_dir() is None
    for filename in ("config.json", "model.bin", "tokenizer.json"):
        (model / filename).write_bytes(b"ready")
    assert bundled_model_dir() == model
