from __future__ import annotations

from collections import deque
from collections.abc import Callable

import numpy as np


class SpeechSegmenter:
    """Turn a continuous 16 kHz stream into speech utterances."""

    def __init__(
        self,
        on_utterance: Callable[[np.ndarray], None],
        sample_rate: int = 16_000,
        aggressiveness: int = 2,
    ) -> None:
        self.on_utterance = on_utterance
        self.sample_rate = sample_rate
        self.frame_ms = 20
        self.frame_samples = sample_rate * self.frame_ms // 1000
        self.pre_roll_frames = 10
        self.end_silence_frames = 18
        self.minimum_frames = 10
        self.maximum_frames = 750
        self._pending = np.zeros(0, dtype=np.float32)
        self._pre_roll: deque[np.ndarray] = deque(maxlen=self.pre_roll_frames)
        self._active: list[np.ndarray] = []
        self._silent_frames = 0
        try:
            import webrtcvad

            self._vad = webrtcvad.Vad(aggressiveness)
        except Exception:
            self._vad = None

    def feed(self, samples: np.ndarray) -> None:
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if not len(samples):
            return
        self._pending = np.concatenate((self._pending, samples))
        while len(self._pending) >= self.frame_samples:
            frame = self._pending[: self.frame_samples]
            self._pending = self._pending[self.frame_samples :]
            self._process_frame(frame)

    def flush(self) -> None:
        if self._active and len(self._active) >= self.minimum_frames:
            self._emit()
        self._pending = np.zeros(0, dtype=np.float32)
        self._active.clear()
        self._pre_roll.clear()
        self._silent_frames = 0

    def _is_speech(self, frame: np.ndarray) -> bool:
        clipped = np.clip(frame, -1.0, 1.0)
        if self._vad is not None:
            pcm = (clipped * 32767).astype("<i2").tobytes()
            try:
                return bool(self._vad.is_speech(pcm, self.sample_rate))
            except Exception:
                pass
        rms = float(np.sqrt(np.mean(np.square(clipped))))
        return rms >= 0.012

    def _process_frame(self, frame: np.ndarray) -> None:
        speech = self._is_speech(frame)
        if not self._active:
            self._pre_roll.append(frame.copy())
            if speech:
                self._active = list(self._pre_roll)
                self._pre_roll.clear()
                self._silent_frames = 0
            return

        self._active.append(frame.copy())
        self._silent_frames = 0 if speech else self._silent_frames + 1
        if (
            self._silent_frames >= self.end_silence_frames
            or len(self._active) >= self.maximum_frames
        ):
            if len(self._active) >= self.minimum_frames:
                self._emit()
            self._active.clear()
            self._silent_frames = 0

    def _emit(self) -> None:
        utterance = np.concatenate(self._active).astype(np.float32, copy=False)
        self.on_utterance(utterance)
