from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from packaging.version import InvalidVersion, Version
from PySide6.QtCore import QObject, QProcess, Signal

from clearcue import __version__
from clearcue.paths import updates_dir


LOGGER = logging.getLogger(__name__)
LATEST_RELEASE_URL = "https://api.github.com/repos/hamzasalahuddin72/prxmpt/releases/latest"
USER_AGENT = f"prxmpt/{__version__} Windows updater"
GITHUB_API_VERSION = "2026-03-10"
SHA256_PATTERN = re.compile(r"^sha256:([0-9a-fA-F]{64})$")


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    tag: str
    title: str
    notes: str
    page_url: str
    installer_name: str
    installer_url: str
    installer_size: int
    sha256: str


def normalise_version(value: str) -> Version:
    cleaned = value.strip()
    if cleaned.lower().startswith("v"):
        cleaned = cleaned[1:]
    return Version(cleaned)


def is_newer_version(candidate: str, current: str = __version__) -> bool:
    try:
        return normalise_version(candidate) > normalise_version(current)
    except InvalidVersion:
        return False


def parse_release(payload: dict) -> ReleaseInfo:
    if payload.get("draft") or payload.get("prerelease"):
        raise ValueError("The latest GitHub release is not a stable published update.")
    tag = str(payload.get("tag_name") or "").strip()
    version = str(normalise_version(tag))
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise ValueError("The release does not contain downloadable assets.")

    expected_installers = (
        f"prxmptupdate_{version}.exe".lower(),
        # v1.0.8 keeps the legacy asset name so installed ClearCue 1.0.7
        # clients can discover the one-time rename update.
        f"clearcueupdate_{version}.exe".lower(),
    )
    candidates: dict[str, dict] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        if name.lower() in expected_installers:
            candidates[name.lower()] = asset
    if not candidates:
        raise ValueError("The release does not contain a prxmpt update installer.")
    asset = next(candidates[name] for name in expected_installers if name in candidates)

    digest = str(asset.get("digest") or "")
    match = SHA256_PATTERN.fullmatch(digest)
    sha256 = match.group(1).lower() if match else ""
    installer_name = Path(str(asset.get("name") or "")).name
    installer_url = str(asset.get("browser_download_url") or "")
    if not installer_name or not installer_url.startswith("https://github.com/"):
        raise ValueError("The release installer URL is invalid.")

    return ReleaseInfo(
        version=version,
        tag=tag,
        title=str(payload.get("name") or f"prxmpt {tag}"),
        notes=str(payload.get("body") or "No release notes were provided."),
        page_url=str(payload.get("html_url") or ""),
        installer_name=installer_name,
        installer_url=installer_url,
        installer_size=max(0, int(asset.get("size") or 0)),
        sha256=sha256,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class UpdateService(QObject):
    update_available = Signal(object)
    no_update = Signal(str)
    check_failed = Signal(str)
    download_progress = Signal(int)
    download_failed = Signal(str)
    installer_ready = Signal(str)
    install_started = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        self._checking = False
        self._downloading = False
        self._stopping = threading.Event()

    def shutdown(self) -> None:
        self._stopping.set()

    def check_for_updates(self) -> None:
        with self._lock:
            if self._checking or self._stopping.is_set():
                return
            self._checking = True
        threading.Thread(
            target=self._check_worker,
            name="clearcue-update-check",
            daemon=True,
        ).start()

    def _check_worker(self) -> None:
        try:
            request = urllib.request.Request(
                LATEST_RELEASE_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": USER_AGENT,
                    "X-GitHub-Api-Version": GITHUB_API_VERSION,
                },
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError("GitHub returned an invalid release response.")
            release = parse_release(payload)
            if self._stopping.is_set():
                return
            if is_newer_version(release.version):
                self.update_available.emit(release)
            else:
                self.no_update.emit(__version__)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                message = "No published prxmpt release is available yet."
            else:
                message = f"Update check failed: GitHub returned HTTP {exc.code}."
            LOGGER.info(message)
            if not self._stopping.is_set():
                self.check_failed.emit(message)
        except Exception as exc:
            message = f"Update check failed: {' '.join(str(exc).split()) or type(exc).__name__}"
            LOGGER.info(message)
            if not self._stopping.is_set():
                self.check_failed.emit(message)
        finally:
            with self._lock:
                self._checking = False

    def download(self, release: ReleaseInfo) -> None:
        with self._lock:
            if self._downloading or self._stopping.is_set():
                return
            self._downloading = True
        threading.Thread(
            target=self._download_worker,
            args=(release,),
            name="clearcue-update-download",
            daemon=True,
        ).start()

    def _download_worker(self, release: ReleaseInfo) -> None:
        destination = updates_dir() / Path(release.installer_name).name
        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            if not release.sha256:
                raise RuntimeError(
                    "GitHub did not provide the installer's SHA-256 digest; use the release page instead."
                )
            if destination.exists() and sha256_file(destination) == release.sha256:
                self.download_progress.emit(100)
                self.installer_ready.emit(str(destination))
                return

            temporary.unlink(missing_ok=True)
            request = urllib.request.Request(
                release.installer_url,
                headers={"Accept": "application/octet-stream", "User-Agent": USER_AGENT},
            )
            digest = hashlib.sha256()
            downloaded = 0
            with urllib.request.urlopen(request, timeout=30) as response, temporary.open("wb") as output:
                expected = release.installer_size or int(response.headers.get("Content-Length") or 0)
                while not self._stopping.is_set():
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if expected:
                        self.download_progress.emit(min(99, int(downloaded * 100 / expected)))
            if self._stopping.is_set():
                raise RuntimeError("Update download was cancelled.")
            if release.installer_size and downloaded != release.installer_size:
                raise RuntimeError("The update download is incomplete.")
            if digest.hexdigest().lower() != release.sha256:
                raise RuntimeError("The update failed SHA-256 verification and was deleted.")
            os.replace(temporary, destination)
            for pattern in ("ClearCueUpdate_*.exe", "prxmptUpdate_*.exe"):
                for old_installer in updates_dir().glob(pattern):
                    if old_installer != destination:
                        old_installer.unlink(missing_ok=True)
            self.download_progress.emit(100)
            self.installer_ready.emit(str(destination))
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            message = " ".join(str(exc).split()) or type(exc).__name__
            LOGGER.warning("Update download failed: %s", message)
            if not self._stopping.is_set():
                self.download_failed.emit(message)
        finally:
            with self._lock:
                self._downloading = False

    def launch_installer(self, installer_path: str) -> bool:
        path = Path(installer_path)
        if not path.is_file() or path.suffix.lower() != ".exe":
            self.download_failed.emit("The verified update installer is no longer available.")
            return False
        arguments = [
            "/SILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CLOSEAPPLICATIONS",
            "/RELAUNCH=1",
        ]
        result = QProcess.startDetached(str(path), arguments)
        started = bool(result[0] if isinstance(result, tuple) else result)
        if started:
            self.install_started.emit()
            return True
        self.download_failed.emit("Windows could not start the update installer.")
        return False
