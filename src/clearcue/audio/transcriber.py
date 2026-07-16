from __future__ import annotations

import logging
import os
import queue
import threading
import time
from collections.abc import Callable

import numpy as np

from clearcue.paths import models_dir


LOGGER = logging.getLogger(__name__)


class FasterWhisperEngine:
    def __init__(self, model_name: str, device: str, compute_type: str) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._model = None

    @property
    def description(self) -> str:
        return f"{self.model_name} on {self.device}/{self.compute_type}"

    def load(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel

        logical_cpus = os.cpu_count() or 4
        cpu_threads = max(1, min(4, logical_cpus - 1 if logical_cpus > 2 else logical_cpus))
        self._model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type,
            cpu_threads=cpu_threads,
            num_workers=1,
            download_root=str(models_dir()),
        )

    def transcribe(self, audio: np.ndarray) -> str:
        self.load()
        segments, _ = self._model.transcribe(
            np.asarray(audio, dtype=np.float32),
            language="en",
            beam_size=1,
            best_of=1,
            temperature=0,
            condition_on_previous_text=False,
            without_timestamps=True,
            word_timestamps=False,
            vad_filter=False,
            max_new_tokens=96,
        )
        return " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()


class TranscriptionWorker:
    def __init__(
        self,
        model_name: str,
        device: str,
        compute_type: str,
        on_transcript: Callable[[str, str], None],
        on_status: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        engine: FasterWhisperEngine | None = None,
        engine_factory: Callable[[str, str, str], FasterWhisperEngine] | None = None,
        queue_size: int = 4,
    ) -> None:
        self._engine_factory = engine_factory or FasterWhisperEngine
        self.engine = engine or self._engine_factory(model_name, device, compute_type)
        self.on_transcript = on_transcript
        self.on_status = on_status or (lambda message: None)
        self.on_error = on_error or (lambda message: None)
        self._queue: queue.Queue[tuple[str, np.ndarray] | None] = queue.Queue(
            maxsize=max(2, queue_size)
        )
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._backlog_reported = False
        self.dropped_segments = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._clear_queue()
        self._thread = threading.Thread(target=self._run, name="transcription", daemon=True)
        self._thread.start()

    def submit(self, speaker: str, audio: np.ndarray) -> None:
        if self._stop.is_set():
            return
        item = (speaker, np.asarray(audio, dtype=np.float32))
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(item)
            except queue.Full:
                return
            self.dropped_segments += 1
            if not self._backlog_reported:
                self._backlog_reported = True
                self.on_status("Live mode: skipped older audio to keep transcription current")

    def stop(self) -> None:
        self._stop.set()
        self._clear_queue()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def _clear_queue(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    def _run(self) -> None:
        self.on_status(f"Preparing fast speech model: {self.engine.description}")
        try:
            self.engine.load()
        except Exception as exc:
            if self.engine.device != "cpu":
                LOGGER.warning("GPU speech model failed; falling back to CPU", exc_info=True)
                try:
                    self._fallback_to_cpu()
                except Exception as fallback_exc:
                    self.on_error(f"Speech model could not load: {fallback_exc}")
                    return
            else:
                self.on_error(f"Speech model could not load: {exc}")
                return

        if self._stop.is_set():
            return
        self.on_status("Listening — fast speech model ready")
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            if item is None:
                break
            speaker, audio = item
            try:
                started = time.perf_counter()
                try:
                    text = self.engine.transcribe(audio)
                except Exception:
                    # CTranslate2 can construct a CUDA model successfully and
                    # only discover missing cuBLAS/cuDNN DLLs on its first
                    # inference. Recover at the point of failure and retry this
                    # segment once instead of losing live transcription.
                    if self.engine.device == "cpu":
                        raise
                    LOGGER.warning(
                        "GPU speech inference failed; retrying on CPU/int8",
                        exc_info=True,
                    )
                    self._fallback_to_cpu()
                    text = self.engine.transcribe(audio)
                elapsed = time.perf_counter() - started
                LOGGER.info(
                    "Transcribed %.2fs of %s audio in %.2fs",
                    len(audio) / 16_000,
                    speaker,
                    elapsed,
                )
                if text:
                    self.on_transcript(speaker, text)
                if self._backlog_reported and self._queue.qsize() <= 1:
                    self._backlog_reported = False
                    self.on_status("Listening — caught up")
            except Exception as exc:
                LOGGER.exception("Transcription failed")
                self.on_error(f"Transcription failed: {exc}")
        self.on_status("Transcription stopped")

    def _fallback_to_cpu(self) -> None:
        self.on_status("GPU unavailable — switching speech recognition to CPU/int8")
        replacement = self._engine_factory(self.engine.model_name, "cpu", "int8")
        replacement.load()
        self.engine = replacement
        self.on_status("Listening — CPU/int8 speech model ready")
