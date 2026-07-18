from pathlib import Path

import pytest

from clearcue.services.updater import is_newer_version, parse_release, sha256_file


def _release_payload() -> dict:
    return {
        "tag_name": "v1.0.6",
        "name": "ClearCue v1.0.6",
        "body": "Reliability update",
        "html_url": "https://github.com/hamzasalahuddin72/hamzasalahuddin72/prxmpt/releases/tag/v1.0.6",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": "ClearCueUpdate_1.0.6.exe",
                "browser_download_url": (
                    "https://github.com/hamzasalahuddin72/hamzasalahuddin72/prxmpt/releases/download/"
                    "v1.0.6/ClearCueUpdate_1.0.6.exe"
                ),
                "size": 1234,
                "digest": "sha256:" + "ab" * 32,
            }
        ],
    }


def test_release_parser_selects_verified_windows_installer() -> None:
    release = parse_release(_release_payload())
    assert release.version == "1.0.6"
    assert release.installer_name == "ClearCueUpdate_1.0.6.exe"
    assert release.installer_size == 1234
    assert release.sha256 == "ab" * 32


def test_release_parser_prefers_new_prxmpt_installer_name() -> None:
    payload = _release_payload()
    payload["assets"].append(
        {
            "name": "prxmptUpdate_1.0.6.exe",
            "browser_download_url": (
                "https://github.com/hamzasalahuddin72/hamzasalahuddin72/prxmpt/releases/download/"
                "v1.0.6/prxmptUpdate_1.0.6.exe"
            ),
            "size": 4321,
            "digest": "sha256:" + "cd" * 32,
        }
    )
    release = parse_release(payload)
    assert release.installer_name == "prxmptUpdate_1.0.6.exe"
    assert release.sha256 == "cd" * 32


def test_release_parser_rejects_missing_installer() -> None:
    payload = _release_payload()
    payload["assets"] = []
    with pytest.raises(ValueError, match="update installer"):
        parse_release(payload)


def test_semantic_version_comparison() -> None:
    assert is_newer_version("v1.0.10", "1.0.9")
    assert not is_newer_version("v1.0.6", "1.0.6")
    assert not is_newer_version("not-a-version", "1.0.6")


def test_sha256_file(tmp_path: Path) -> None:
    path = tmp_path / "update.exe"
    path.write_bytes(b"clearcue")
    assert sha256_file(path) == "fbe9416f29ccd99ef6e712cb8d3261653331e952000bd7ca86020e11d30f625d"
