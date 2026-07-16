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
    ) -> None:
        self.config = config
        self.on_transcript = on_transcript
        self.on_status = on_status or (lambda message: None)
        self.on_level = on_level or (lambda source, level: None)
        self.on_error = on_error or (lambda message: None)
        self.on_source_state = on_source_state or (
            lambda kind, available, message: None
        )
        self.transcriber = TranscriptionWorker(
            config.whisper_model,
            config.whisper_device,
            config.whisper_compute_type,
            self.on_transcript,
            self.on_status,
            self.on_error,
        )
        self.segmenters = {
            "Interviewer": SpeechSegmenter(
                lambda audio: self.transcriber.submit("Interviewer", audio)
            ),
            "You": SpeechSegmenter(lambda audio: self.transcriber.submit("You", audio)),
        }
        self.captures: list[AudioCapture] = []
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self.transcriber.start()
        system_capture = AudioCapture(
            self.config.speaker_id,
            "loopback",
            self.config.sample_rate,
            lambda data: self.segmenters["Interviewer"].feed(data),
            lambda level: self.on_level("Interviewer", level),
            self.on_error,
            self.on_source_state,
        )
        microphone_capture = AudioCapture(
            self.config.microphone_id,
            "microphone",
            self.config.sample_rate,
            lambda data: self.segmenters["You"].feed(data),
            lambda level: self.on_level("You", level),
            self.on_error,
            self.on_source_state,
        )
        self.captures = [system_capture, microphone_capture]
        for capture in self.captures:
            capture.start()
        self._running = True
        self.on_status("Starting audio and fast transcription…")

    def stop(self) -> None:
        if not self._running:
            return
        for capture in self.captures:
            capture.stop()
        for segmenter in self.segmenters.values():
            segmenter.flush()
        self.transcriber.stop()
        self.captures.clear()
        self._running = False
        self.on_status("Session stopped")
