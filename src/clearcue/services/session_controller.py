from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from clearcue.audio.coordinator import AudioCoordinator
from clearcue.config import AppConfig, ConfigStore
from clearcue.intelligence.answer_service import AnswerService
from clearcue.intelligence.question_detector import detect_question
from clearcue.storage.database import Database


class SessionController(QObject):
    QUESTION_PAUSE_MS = 850

    transcript_ready = Signal(str, str, bool)
    question_ready = Signal(str)
    answer_ready = Signal(str, str, object)
    status_changed = Signal(str)
    level_changed = Signal(str, float)
    source_state_changed = Signal(str, bool, str)
    error_raised = Signal(str)
    session_state_changed = Signal(bool)
    transcribing_changed = Signal(bool)

    _incoming_transcript = Signal(str, str)
    _incoming_status = Signal(str)
    _incoming_level = Signal(str, float)
    _incoming_source_state = Signal(str, bool, str)
    _incoming_error = Signal(str)
    _incoming_answer = Signal(str, str, object)
    _incoming_transcribing = Signal(bool)

    def __init__(
        self,
        database: Database,
        config_store: ConfigStore,
        config: AppConfig,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.database = database
        self.config_store = config_store
        self.config = config
        self.profile_id = database.ensure_default_profile()
        self.session_id: int | None = None
        self.audio: AudioCoordinator | None = None
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="clearcue-ai")
        self._question_parts: list[str] = []
        self._question_timer = QTimer(self)
        self._question_timer.setSingleShot(True)
        self._question_timer.setInterval(self.QUESTION_PAUSE_MS)
        self._question_timer.timeout.connect(self._finalize_pending_question)
        self._incoming_transcript.connect(self._handle_transcript)
        self._incoming_status.connect(self.status_changed.emit)
        self._incoming_level.connect(self.level_changed.emit)
        self._incoming_source_state.connect(self.source_state_changed.emit)
        self._incoming_error.connect(self.error_raised.emit)
        self._incoming_answer.connect(self._handle_answer)
        self._incoming_transcribing.connect(self.transcribing_changed.emit)

    @property
    def running(self) -> bool:
        return bool(self.audio and self.audio.running)

    def set_profile(self, profile_id: int) -> None:
        self.profile_id = profile_id

    def update_config(self, config: AppConfig) -> None:
        self.config = config
        self.config_store.save(config)

    def set_audio_source_enabled(self, kind: str, enabled: bool) -> None:
        if kind == "microphone":
            self.config.microphone_enabled = enabled
        elif kind == "loopback":
            self.config.speaker_enabled = enabled
        else:
            raise ValueError(f"Unknown audio source: {kind}")
        self.config_store.save(self.config)
        if self.audio and self.audio.running:
            self.audio.set_source_enabled(kind, enabled)

    def start(self) -> None:
        if self.running:
            return
        if not self.config.consent_acknowledged:
            self.error_raised.emit(
                "Confirm that recording/transcription is permitted and participants are informed."
            )
            return
        if self.config.save_transcripts:
            self.session_id = self.database.create_session(self.profile_id)
        else:
            self.session_id = None
        self._question_parts.clear()
        self._question_timer.stop()
        self.audio = AudioCoordinator(
            self.config,
            self._incoming_transcript.emit,
            self._incoming_status.emit,
            self._incoming_level.emit,
            self._incoming_error.emit,
            self._incoming_source_state.emit,
            self._incoming_transcribing.emit,
        )
        try:
            self.audio.start()
        except Exception as exc:
            self.audio = None
            self.error_raised.emit(f"The session could not start: {exc}")
            return
        self.session_state_changed.emit(True)

    def stop(self) -> None:
        self._question_timer.stop()
        self._question_parts.clear()
        if self.audio:
            self.audio.stop()
            self.audio = None
        if self.session_id is not None:
            self.database.finish_session(self.session_id)
        self.session_id = None
        self.level_changed.emit("Interviewer", 0.0)
        self.level_changed.emit("You", 0.0)
        self.session_state_changed.emit(False)
        self.transcribing_changed.emit(False)

    def ask(self, question: str, style: str | None = None) -> None:
        cleaned = " ".join(question.split())
        if not cleaned:
            self.error_raised.emit("Enter or detect a question first.")
            return
        self.status_changed.emit("Building a grounded answer…")
        config = self.config
        chunks = self.database.context_chunks(self.profile_id)

        def task() -> tuple[str, str, tuple[str, ...]]:
            result = AnswerService(config, chunks).generate(cleaned, style)
            return result.question, result.answer, result.sources

        future = self._executor.submit(task)

        def complete(completed) -> None:
            try:
                question, answer, sources = completed.result()
                self._incoming_answer.emit(question, answer, sources)
                self._incoming_status.emit("Answer ready")
            except Exception as exc:
                self._incoming_error.emit(str(exc))
                self._incoming_status.emit("Answer generation failed")

        future.add_done_callback(complete)

    @Slot(str, str)
    def _handle_transcript(self, speaker: str, text: str) -> None:
        cleaned = " ".join(text.split())
        question = None
        if speaker == "Interviewer" and cleaned:
            self._question_parts.append(cleaned)
            candidate = " ".join(self._question_parts)
            question = detect_question(candidate)
            self._question_timer.start()
            if question:
                # Show the question as it forms, but wait for the longer pause
                # before triggering automatic answer generation.
                self.question_ready.emit(question)
        is_question = question is not None
        if self.session_id is not None:
            self.database.add_transcript(self.session_id, speaker, cleaned, is_question)
        self.transcript_ready.emit(speaker, cleaned, is_question)

    @Slot()
    def _finalize_pending_question(self) -> None:
        candidate = " ".join(self._question_parts)
        self._question_parts.clear()
        question = detect_question(candidate)
        if not question:
            return
        self.question_ready.emit(question)
        if self.config.auto_generate:
            self.ask(question)

    @Slot(str, str, object)
    def _handle_answer(self, question: str, answer: str, sources: object) -> None:
        source_tuple = tuple(str(source) for source in (sources or ()))
        if self.session_id is not None:
            self.database.add_session_answer(
                self.session_id,
                question,
                answer,
                source_tuple,
            )
        self.answer_ready.emit(question, answer, source_tuple)

    def shutdown(self) -> None:
        self.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
