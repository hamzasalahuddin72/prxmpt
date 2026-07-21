from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from clearcue.intelligence.conversation_gate import ConversationGate, clean_text


@dataclass(frozen=True, slots=True)
class ContextTurn:
    """A compact, provider-safe representation of one completed session turn."""

    turn_index: int
    question: str
    resolved_question: str
    answer: str = ""
    turn_id: int | None = None
    topic_lock_turn_index: int | None = None


@dataclass(frozen=True, slots=True)
class TurnResolution:
    question: str
    resolved_question: str
    is_follow_up: bool
    parent_turn_index: int | None
    topic_lock_turn_index: int | None
    reason: str
    context: tuple[dict[str, Any], ...]
    status: str = "accepted_new_topic"
    follow_up_score: float = 0.0
    repair_confidence: float = 0.0
    clarification_message: str = ""
    metadata: Mapping[str, Any] | None = None

    @property
    def is_answerable(self) -> bool:
        return self.status != "clarification_needed"


class TurnContextWindow:
    """Bounded per-session context with deterministic follow-up classification."""

    def __init__(self, *, max_turns: int = 6, max_chars: int = 4_800) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        if max_chars < 200:
            raise ValueError("max_chars must be at least 200")
        self.max_turns = max_turns
        self.max_chars = max_chars
        self._turns: list[ContextTurn] = []
        self._gate = ConversationGate()

    @property
    def turns(self) -> tuple[ContextTurn, ...]:
        return tuple(self._turns)

    def reset(self) -> None:
        """Start a clean context boundary for a new listening session."""

        self._turns.clear()

    def resolve(self, question: str) -> TurnResolution:
        cleaned = clean_text(question)
        if not cleaned:
            raise ValueError("Question cannot be empty")
        decision = self._gate.evaluate(cleaned, self._turns)
        return TurnResolution(
            question=decision.raw_question,
            resolved_question=decision.resolved_question,
            is_follow_up=decision.is_follow_up,
            parent_turn_index=decision.parent_turn_index,
            topic_lock_turn_index=decision.topic_lock_turn_index,
            reason=decision.reason,
            context=self.context_payload(decision.topic_lock_turn_index),
            status=decision.status,
            follow_up_score=decision.follow_up_score,
            repair_confidence=decision.repair_confidence,
            clarification_message=decision.clarification_message,
            metadata=decision.metadata,
        )

    def add_turn(
        self,
        question: str,
        *,
        resolved_question: str = "",
        turn_id: int | None = None,
        follow_up_of_turn_index: int | None = None,
        topic_lock_turn_index: int | None = None,
        answer: str = "",
    ) -> ContextTurn:
        cleaned = clean_text(question)
        if not cleaned:
            raise ValueError("Question cannot be empty")
        turn = ContextTurn(
            turn_index=(self._turns[-1].turn_index + 1 if self._turns else 1),
            question=cleaned,
            resolved_question=clean_text(resolved_question) or cleaned,
            answer=clean_text(answer),
            turn_id=turn_id,
            topic_lock_turn_index=topic_lock_turn_index,
        )
        self._turns.append(turn)
        return turn

    def complete_turn(self, question: str, answer: str) -> ContextTurn | None:
        """Attach an answer to the latest matching turn."""

        cleaned_question = clean_text(question)
        for index in range(len(self._turns) - 1, -1, -1):
            turn = self._turns[index]
            if (
                cleaned_question not in {turn.question, turn.resolved_question}
                or turn.answer
            ):
                continue
            updated = ContextTurn(
                turn_index=turn.turn_index,
                question=turn.question,
                resolved_question=turn.resolved_question,
                answer=clean_text(answer),
                turn_id=turn.turn_id,
                topic_lock_turn_index=turn.topic_lock_turn_index,
            )
            self._turns[index] = updated
            return updated
        return None

    def context_payload(
        self,
        topic_lock_turn_index: int | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Return chronological, size-bounded context for prompt construction."""

        selected: list[dict[str, Any]] = []
        total_chars = 0
        candidates = self._turns[-self.max_turns :]
        if topic_lock_turn_index is not None:
            candidates = [
                turn
                for turn in candidates
                if turn.turn_index == topic_lock_turn_index
                or turn.topic_lock_turn_index == topic_lock_turn_index
            ]
        for turn in reversed(candidates):
            answer = self._compact_text(turn.answer, 900)
            entry: dict[str, Any] = {
                "turn_index": turn.turn_index,
                "question": self._compact_text(turn.question, 500),
                "resolved_question": self._compact_text(turn.resolved_question, 500),
                "answer": answer,
                # The active resolution can lock its root turn even though the
                # root was originally a standalone question and therefore did
                # not store a lock of its own.
                "topic_lock_turn_index": (
                    topic_lock_turn_index or turn.topic_lock_turn_index
                ),
            }
            entry_chars = sum(len(str(value)) for value in entry.values())
            if selected and total_chars + entry_chars > self.max_chars:
                break
            selected.append(entry)
            total_chars += entry_chars
        selected.reverse()
        return tuple(selected)

    def load_turns(self, turns: Iterable[ContextTurn]) -> None:
        """Replace the window from persisted turns at a session boundary."""

        self._turns = list(turns)[-self.max_turns :]

    @staticmethod
    def _compact_text(text: str, limit: int) -> str:
        cleaned = clean_text(text)
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1].rstrip() + "…"
