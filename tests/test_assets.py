import base64
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

from clearcue.resources import bundled_model_dir, resource_path


def test_approved_svg_assets_are_byte_exact() -> None:
    manifest_path = resource_path("asset_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest) == 12
    for filename, expected in manifest.items():
        actual = hashlib.sha256(resource_path(filename).read_bytes()).hexdigest()
        assert actual == expected, filename


def test_extracted_controls_are_the_original_embedded_svg_images() -> None:
    manifest = json.loads(resource_path("asset_manifest.json").read_text(encoding="utf-8"))
    expected = {digest for name, digest in manifest.items() if name != "prxmpt-logo.png"}
    root = ET.parse(resource_path("prxmpt-ui.svg")).getroot()
    embedded = set()
    for element in root.iter():
        if not element.tag.endswith("image"):
            continue
        href = element.attrib.get("{http://www.w3.org/1999/xlink}href", "")
        payload = base64.b64decode(href.split(",", 1)[1])
        embedded.add(hashlib.sha256(payload).hexdigest())
    assert embedded == expected


def test_bundled_model_requires_complete_local_snapshot(monkeypatch, tmp_path) -> None:
    model = tmp_path / "models" / "faster-whisper-tiny.en"
    model.mkdir(parents=True)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert bundled_model_dir() is None
    for filename in ("config.json", "model.bin", "tokenizer.json"):
        (model / filename).write_bytes(b"ready")
    assert bundled_model_dir() == model
