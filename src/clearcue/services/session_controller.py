from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from clearcue.audio.coordinator import AudioCoordinator
from clearcue.config import AppConfig, ConfigStore
from clearcue.intelligence.answer_service import AnswerService
from clearcue.intelligence.question_detector import (
    detect_question,
    potential_question_candidate,
    question_fragment,
)
from clearcue.intelligence.turn_context import TurnContextWindow, TurnResolution
from clearcue.storage.database import Database


def configured_answer_model(config: AppConfig) -> str:
    if config.answer_provider == "gemini":
        return config.gemini_model
    if config.answer_provider == "openai":
        return config.openai_model
    if config.answer_provider == "ollama":
        return config.ollama_model
    return "local"


class SessionController(QObject):
    QUESTION_PAUSE_MS = 1150

    transcript_ready = Signal(str, str, bool)
    question_ready = Signal(str)
    answer_ready = Signal(str, str, object)
    answer_started = Signal(str)
    answer_delta = Signal(str, str)
    answer_failed = Signal(str)
    status_changed = Signal(str)
    level_changed = Signal(str, float)
    source_state_changed = Signal(str, bool, str)
    error_raised = Signal(str)
    session_state_changed = Signal(bool)
    transcribing_changed = Signal(bool)
    live_transcript_changed = Signal(object, str, str)

    _incoming_transcript = Signal(str, str)
    _incoming_status = Signal(str)
    _incoming_level = Signal(str, float)
    _incoming_source_state = Signal(str, bool, str)
    _incoming_error = Signal(str)
    _incoming_answer = Signal(int, str, str, object, str)
    _incoming_answer_delta = Signal(int, str, str)
    _incoming_answer_error = Signal(int, str)
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
        self._live_transcript_parts: list[tuple[str, bool]] = []
        self._turn_context = TurnContextWindow()
        self._pending_conversation_context: tuple[dict[str, object], ...] = ()
        self._prepared_turn_question = ""
        self._active_turn_id: int | None = None
        self._active_turn_question = ""
        self._answer_request_id = 0
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
        self._incoming_answer_delta.connect(self._handle_answer_delta)
        self._incoming_answer_error.connect(self._handle_answer_error)
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
            self.session_id = self.database.create_session(
                self.profile_id,
                model_used=configured_answer_model(self.config),
            )
        else:
            self.session_id = None
        self._turn_context.reset()
        self._pending_conversation_context = ()
        self._prepared_turn_question = ""
        self._active_turn_id = None
        self._active_turn_question = ""
        self._question_parts.clear()
        self._live_transcript_parts.clear()
        self._question_timer.stop()
        self._emit_live_transcript()
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
        if self.audio:
            self.audio.stop()
            self.audio = None
        self._commit_pending_question(auto_generate=False)
        if self.session_id is not None:
            self.database.finish_session(self.session_id)
        self.session_id = None
        self._turn_context.reset()
        self._pending_conversation_context = ()
        self._prepared_turn_question = ""
        self._active_turn_id = None
        self._active_turn_question = ""
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
        self._answer_request_id += 1
        request_id = self._answer_request_id
        self.answer_started.emit(cleaned)
        config = replace(self.config)
        answer_model = configured_answer_model(config)
        chunks = self.database.context_chunks(self.profile_id)
        prepared_turn = self._prepared_turn_question == cleaned
        if prepared_turn:
            conversation_context = self._pending_conversation_context
        else:
            resolution, _turn_id = self._register_turn(cleaned)
            conversation_context = resolution.context
        self._pending_conversation_context = ()
        self._prepared_turn_question = ""
        if not conversation_context:
            conversation_context = self._turn_context.context_payload()

        def task() -> tuple[str, str, tuple[str, ...]]:
            result = AnswerService(config, chunks).generate_stream(
                cleaned,
                style,
                lambda delta: self._incoming_answer_delta.emit(
                    request_id,
                    cleaned,
                    delta,
                ),
                conversation_context=conversation_context,
            )
            return result.question, result.answer, result.sources

        future = self._executor.submit(task)

        def complete(completed) -> None:
            try:
                question, answer, sources = completed.result()
                self._incoming_answer.emit(
                    request_id,
                    question,
                    answer,
                    sources,
                    answer_model,
                )
            except Exception as exc:
                self._incoming_answer_error.emit(request_id, str(exc))

        future.add_done_callback(complete)

    def cancel_answer(self) -> None:
        """Ignore any remaining output from the active cloud request."""

        self._answer_request_id += 1
        self.status_changed.emit("Answer cleared")

    def clear_live_transcript(self) -> None:
        """Clear only the on-screen transcript, preserving saved history."""

        self._question_timer.stop()
        self._question_parts.clear()
        self._live_transcript_parts.clear()
        self._emit_live_transcript()

    @Slot(str, str)
    def _handle_transcript(self, speaker: str, text: str) -> None:
        cleaned = " ".join(text.split())
        question = None
        if speaker == "Interviewer" and cleaned:
            self._question_parts.append(cleaned)
            candidate = " ".join(self._question_parts)
            question = detect_question(candidate)
            active_parts = self._question_display_parts(
                candidate,
                question,
                forming=True,
            )
            if active_parts[-1][1] and all(
                not emphasized for _text, emphasized in active_parts[:-1]
            ):
                active_regular = " ".join(
                    text for text, _emphasized in active_parts[:-1]
                )
                self._emit_live_transcript(
                    active_regular,
                    active_parts[-1][0],
                )
            else:
                self.live_transcript_changed.emit(
                    tuple([*self._live_transcript_parts, *active_parts]),
                    "",
                    "",
                )
            self._question_timer.start()
            if question:
                # Show the question as it forms, but wait for the longer pause
                # before triggering automatic answer generation.
                self.question_ready.emit(question)
        elif cleaned:
            # A reply from the user ends the interviewer's current sentence.
            self._question_timer.stop()
            self._commit_pending_question(auto_generate=True)
            self._live_transcript_parts.append((cleaned, False))
            self._emit_live_transcript()
        is_question = question is not None
        if self.session_id is not None and speaker != "Interviewer" and cleaned:
            self.database.add_transcript(self.session_id, speaker, cleaned, is_question)
        self.transcript_ready.emit(speaker, cleaned, is_question)

    @Slot()
    def _finalize_pending_question(self) -> None:
        self._commit_pending_question(auto_generate=True)

    def _commit_pending_question(self, *, auto_generate: bool) -> None:
        if not self._question_parts:
            return
        candidate = " ".join(self._question_parts)
        self._question_parts.clear()
        question = detect_question(candidate)
        self._live_transcript_parts.extend(
            self._question_display_parts(candidate, question, forming=False)
        )
        self._emit_live_transcript()
        if self.session_id is not None:
            self.database.add_transcript(
                self.session_id,
                "Interviewer",
                candidate,
                question is not None,
            )
        if question:
            resolution, _turn_id = self._register_turn(question)
            self._pending_conversation_context = resolution.context
            self._prepared_turn_question = question
            self.question_ready.emit(question)
            if auto_generate and self.config.auto_generate:
                self.ask(question)

    def _register_turn(self, question: str) -> tuple[TurnResolution, int | None]:
        resolution = self._turn_context.resolve(question)
        parent_turn_id = None
        if resolution.parent_turn_index is not None:
            parent_turn = next(
                (
                    turn
                    for turn in reversed(self._turn_context.turns)
                    if turn.turn_index == resolution.parent_turn_index
                ),
                None,
            )
            parent_turn_id = parent_turn.turn_id if parent_turn else None
        turn_id = None
        if self.session_id is not None:
            turn_id = self.database.create_session_turn(
                self.session_id,
                question,
                resolved_question=resolution.resolved_question,
                follow_up_of_turn_id=parent_turn_id,
                follow_up_reason=resolution.reason,
                context=resolution.context,
            )
        self._turn_context.add_turn(
            question,
            resolved_question=resolution.resolved_question,
            turn_id=turn_id,
        )
        self._active_turn_id = turn_id
        self._active_turn_question = question
        if self.session_id is not None:
            self.database.save_session_context(
                self.session_id,
                self._turn_context.context_payload(),
            )
        return resolution, turn_id

    @staticmethod
    def _question_display_parts(
        candidate: str,
        question: str | None,
        *,
        forming: bool,
    ) -> list[tuple[str, bool]]:
        """Split raw transcript text without replacing it with reconstructed text."""

        emphasized = (
            potential_question_candidate(candidate)
            if forming
            else None
        )
        if not emphasized and question:
            emphasized = question_fragment(candidate)
        if not emphasized:
            return [(candidate, False)]
        start = candidate.rfind(emphasized)
        if start < 0:
            return [(candidate, False)]
        end = start + len(emphasized)
        parts: list[tuple[str, bool]] = []
        if prefix := candidate[:start].strip():
            parts.append((prefix, False))
        parts.append((candidate[start:end].strip(), True))
        if suffix := candidate[end:].strip():
            parts.append((suffix, False))
        return parts

    def _emit_live_transcript(
        self,
        active_regular: str = "",
        active_question: str = "",
    ) -> None:
        self.live_transcript_changed.emit(
            tuple(self._live_transcript_parts),
            active_regular,
            active_question,
        )

    @Slot(int, str, str)
    def _handle_answer_delta(self, request_id: int, question: str, delta: str) -> None:
        if request_id == self._answer_request_id:
            self.answer_delta.emit(question, delta)

    @Slot(int, str)
    def _handle_answer_error(self, request_id: int, message: str) -> None:
        if request_id != self._answer_request_id:
            return
        self.answer_failed.emit(message)
        self.error_raised.emit(message)
        self.status_changed.emit("Answer generation failed")

    @Slot(int, str, str, object, str)
    def _handle_answer(
        self,
        request_id: int,
        question: str,
        answer: str,
        sources: object,
        model_used: str,
    ) -> None:
        if request_id != self._answer_request_id:
            return
        source_tuple = tuple(str(source) for source in (sources or ()))
        completed_turn = self._turn_context.complete_turn(question, answer)
        turn_id = completed_turn.turn_id if completed_turn else None
        if self.session_id is not None:
            self.database.add_session_answer(
                self.session_id,
                question,
                answer,
                source_tuple,
                model_used,
                turn_id=turn_id,
            )
            if turn_id is not None:
                self.database.update_session_turn(turn_id, answer=answer)
            self.database.save_session_context(
                self.session_id,
                self._turn_context.context_payload(),
            )
        self.answer_ready.emit(question, answer, source_tuple)
        self.status_changed.emit("Answer ready")

    def shutdown(self) -> None:
        self.cancel_answer()
        self.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
