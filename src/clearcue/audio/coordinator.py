from __future__ import annotations

from collections.abc import Callable

from clearcue.audio.capture import AudioCapture
from clearcue.audio.segmenter import SpeechSegmenter
from clearcue.audio.transcriber import TranscriptionWorker
from clearcue.config import AppConfig


class AudioCoordinator:
    def __init__(
        self,
        config: AppConfig,
        on_transcript: Callable[[str, str], None],
        on_status: Callable[[str], None] | None = None,
        on_level: Callable[[str, float], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_source_state: Callable[[str, bool, str], None] | None = None,
        on_transcribing: Callable[[bool], None] | None = None,
    ) -> None:
        self.config = config
        self.on_transcript = on_transcript
        self.on_status = on_status or (lambda message: None)
        self.on_level = on_level or (lambda source, level: None)
        self.on_error = on_error or (lambda message: None)
        self.on_source_state = on_source_state or (
            lambda kind, available, message: None
        )
        self.on_transcribing = on_transcribing or (lambda active: None)
        self.transcriber = TranscriptionWorker(
            config.whisper_model,
            config.whisper_device,
            config.whisper_compute_type,
            self.on_transcript,
            self.on_status,
            self.on_error,
            self.on_transcribing,
        )
        self.segmenters = {
            "Interviewer": SpeechSegmenter(
                lambda audio: self.transcriber.submit("Interviewer", audio)
            ),
            "You": SpeechSegmenter(lambda audio: self.transcriber.submit("You", audio)),
        }
        self.captures: dict[str, AudioCapture] = {}
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self.transcriber.start()
        self._running = True
        if self.config.speaker_enabled:
            self.set_source_enabled("loopback", True)
        else:
            self.on_source_state("loopback", False, "Meeting audio disabled")
        if self.config.microphone_enabled:
            self.set_source_enabled("microphone", True)
        else:
            self.on_source_state("microphone", False, "Microphone disabled")
        self.on_status("Starting audio and fast transcription…")

    def _create_capture(self, kind: str) -> AudioCapture:
        microphone = kind == "microphone"
        return AudioCapture(
            self.config.microphone_id if microphone else self.config.speaker_id,
            kind,
            self.config.sample_rate,
            lambda data: self.segmenters["You" if microphone else "Interviewer"].feed(data),
            lambda level: self.on_level("You" if microphone else "Interviewer", level),
            self.on_error,
            self.on_source_state,
        )

    def set_source_enabled(self, kind: str, enabled: bool) -> None:
        if kind not in {"microphone", "loopback"}:
            raise ValueError(f"Unknown audio source: {kind}")
        capture = self.captures.get(kind)
        if enabled:
            if capture and capture.running:
                return
            capture = self._create_capture(kind)
            self.captures[kind] = capture
            capture.start()
            return
        if capture:
            capture.stop()
            self.captures.pop(kind, None)
        speaker = "You" if kind == "microphone" else "Interviewer"
        self.segmenters[speaker].flush()
        self.on_level(speaker, 0.0)
        self.on_source_state(
            kind,
            False,
            "Microphone disabled" if kind == "microphone" else "Meeting audio disabled",
        )

    def stop(self) -> None:
        if not self._running:
            return
        for capture in tuple(self.captures.values()):
            capture.stop()
        for segmenter in self.segmenters.values():
            segmenter.flush()
        self.transcriber.stop()
        self.on_transcribing(False)
        self.captures.clear()
        self._running = False
        self.on_status("Session stopped")
