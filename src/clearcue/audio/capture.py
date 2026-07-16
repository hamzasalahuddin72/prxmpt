from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

import numpy as np

from clearcue.audio.devices import open_device


LOGGER = logging.getLogger(__name__)
TARGET_SAMPLE_RATE = 16_000


def sample_rate_candidates(preferred: int) -> tuple[int, ...]:
    """Return practical WASAPI rates, preserving order and removing duplicates."""
    rates = (preferred, 48_000, 44_100, 16_000)
    return tuple(dict.fromkeys(rate for rate in rates if rate > 0))


def resample_linear(samples: np.ndarray, source_rate: int, target_rate: int = 16_000) -> np.ndarray:
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if not len(samples) or source_rate == target_rate:
        return samples.copy()
    target_length = max(1, round(len(samples) * target_rate / source_rate))
    old_positions = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
    new_positions = np.linspace(0.0, 1.0, num=target_length, endpoint=False)
    return np.interp(new_positions, old_positions, samples).astype(np.float32)


class AudioCapture:
    def __init__(
        self,
        device_id: str,
        kind: str,
        sample_rate: int,
        on_audio: Callable[[np.ndarray], None],
        on_level: Callable[[float], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_state: Callable[[str, bool, str], None] | None = None,
    ) -> None:
        self.device_id = device_id
        self.kind = kind
        self.sample_rate = sample_rate
        self.on_audio = on_audio
        self.on_level = on_level or (lambda level: None)
        self.on_error = on_error or (lambda message: None)
        self.on_state = on_state or (lambda kind, available, message: None)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._available = False
        self._last_state_message = ""

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=f"capture-{self.kind}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _set_state(self, available: bool, message: str) -> None:
        if available == self._available and message == self._last_state_message:
            return
        self._available = available
        self._last_state_message = message
        self.on_state(self.kind, available, message)

    @property
    def _display_name(self) -> str:
        return "Microphone" if self.kind == "microphone" else "Meeting audio"

    def _device_candidates(self) -> tuple[str, ...]:
        return (self.device_id, "") if self.device_id else ("",)

    def _run(self) -> None:
        retry_delay = 0.5
        try:
            while not self._stop.is_set():
                errors: list[str] = []
                for device_id in self._device_candidates():
                    for rate in sample_rate_candidates(self.sample_rate):
                        if self._stop.is_set():
                            return
                        try:
                            self._record(device_id, rate)
                            if self._stop.is_set():
                                return
                        except Exception as exc:
                            message = " ".join(str(exc).split()) or type(exc).__name__
                            errors.append(f"{rate} Hz: {message}")
                            LOGGER.warning(
                                "%s capture attempt failed (device=%r, rate=%s): %s",
                                self.kind,
                                device_id or "default",
                                rate,
                                message,
                            )

                if self._stop.is_set():
                    return
                detail = errors[-1] if errors else "Windows returned no audio data."
                self._set_state(
                    False,
                    f"{self._display_name} unavailable; retrying automatically. {detail}",
                )
                if self._stop.wait(retry_delay):
                    return
                retry_delay = min(4.0, retry_delay * 2)
        except Exception as exc:
            # Keep all backend failures inside the worker so a CFFI/WASAPI error
            # cannot terminate the Qt application.
            LOGGER.exception("Unexpected %s capture worker failure", self.kind)
            if not self._stop.is_set():
                self.on_error(f"{self._display_name} worker failed safely: {exc}")
        finally:
            self.on_level(0.0)
            if self._stop.is_set():
                self._set_state(False, f"{self._display_name} stopped")

    def _record(self, device_id: str, sample_rate: int) -> None:
        device = open_device(device_id, self.kind)
        # SoundCard recommends numframes substantially smaller than blocksize for
        # low latency. Record all native channels and downmix here because its
        # Windows/WASAPI backend is unreliable when asked for one channel.
        chunk_frames = max(320, int(sample_rate * 0.02))
        with device.recorder(
            samplerate=sample_rate,
            blocksize=chunk_frames * 4,
        ) as recorder:
            next_level_update = 0.0
            empty_since: float | None = None
            while not self._stop.is_set():
                data = recorder.record(numframes=chunk_frames)
                if data is None or not len(data):
                    empty_since = empty_since or time.monotonic()
                    if time.monotonic() - empty_since >= 2.0:
                        raise RuntimeError("The device opened but returned no audio frames.")
                    continue
                empty_since = None
                array = np.asarray(data, dtype=np.float32)
                mono = array if array.ndim == 1 else np.mean(array, axis=1)
                mono = np.nan_to_num(mono, nan=0.0, posinf=0.0, neginf=0.0)
                now = time.monotonic()
                if now >= next_level_update:
                    level = min(1.0, float(np.sqrt(np.mean(np.square(mono)))) * 8.0)
                    self.on_level(level)
                    next_level_update = now + 0.1
                self._set_state(True, f"{self._display_name} connected at {sample_rate} Hz")
                try:
                    self.on_audio(resample_linear(mono, sample_rate, TARGET_SAMPLE_RATE))
                except Exception as exc:
                    LOGGER.exception("Audio consumer rejected a %s chunk", self.kind)
                    self.on_error(f"{self._display_name} processing recovered from an error: {exc}")
