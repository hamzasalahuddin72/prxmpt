from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


_FOLLOW_UP_PREFIXES = (
    "and ",
    "but ",
    "so ",
    "what about ",
    "how about ",
    "why is that",
    "why was that",
    "why did you",
    "how did you",
    "how would that",
    "can you explain",
    "could you explain",
    "can you expand",
    "could you expand",
    "can you say more",
    "could you say more",
    "tell me more",
    "what do you mean",
    "does that mean",
    "in that case",
)

_REFERENCE_TERMS = frozenset(
    {
        "it",
        "that",
        "this",
        "these",
        "those",
        "they",
        "them",
        "there",
        "same",
        "more",
        "also",
        "then",
    }
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.casefold())


@dataclass(frozen=True, slots=True)
class ContextTurn:
    """A compact, provider-safe representation of one completed session turn."""

    turn_index: int
    question: str
    resolved_question: str
    answer: str = ""
    turn_id: int | None = None


@dataclass(frozen=True, slots=True)
class TurnResolution:
    question: str
    resolved_question: str
    is_follow_up: bool
    parent_turn_index: int | None
    reason: str
    context: tuple[dict[str, Any], ...]


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

    @property
    def turns(self) -> tuple[ContextTurn, ...]:
        return tuple(self._turns)

    def reset(self) -> None:
        """Start a clean context boundary for a new listening session."""

        self._turns.clear()

    def resolve(self, question: str) -> TurnResolution:
        cleaned = _clean(question)
        if not cleaned:
            raise ValueError("Question cannot be empty")

        previous = self._turns[-1] if self._turns else None
        is_follow_up = previous is not None and self._looks_like_follow_up(cleaned)
        parent_index = previous.turn_index if is_follow_up and previous else None
        if is_follow_up:
            reason = "short or referential question follows the previous turn"
        else:
            reason = "standalone question or no prior turn available"
        return TurnResolution(
            question=cleaned,
            resolved_question=cleaned,
            is_follow_up=is_follow_up,
            parent_turn_index=parent_index,
            reason=reason,
            context=self.context_payload(),
        )

    def add_turn(
        self,
        question: str,
        *,
        resolved_question: str = "",
        turn_id: int | None = None,
        follow_up_of_turn_index: int | None = None,
        answer: str = "",
    ) -> ContextTurn:
        cleaned = _clean(question)
        if not cleaned:
            raise ValueError("Question cannot be empty")
        turn = ContextTurn(
            turn_index=(self._turns[-1].turn_index + 1 if self._turns else 1),
            question=cleaned,
            resolved_question=_clean(resolved_question) or cleaned,
            answer=_clean(answer),
            turn_id=turn_id,
        )
        self._turns.append(turn)
        return turn

    def complete_turn(self, question: str, answer: str) -> ContextTurn | None:
        """Attach an answer to the latest matching turn."""

        cleaned_question = _clean(question)
        for index in range(len(self._turns) - 1, -1, -1):
            turn = self._turns[index]
            if turn.question != cleaned_question or turn.answer:
                continue
            updated = ContextTurn(
                turn_index=turn.turn_index,
                question=turn.question,
                resolved_question=turn.resolved_question,
                answer=_clean(answer),
                turn_id=turn.turn_id,
            )
            self._turns[index] = updated
            return updated
        return None

    def context_payload(self) -> tuple[dict[str, Any], ...]:
        """Return chronological, size-bounded context for prompt construction."""

        selected: list[dict[str, Any]] = []
        total_chars = 0
        for turn in reversed(self._turns[-self.max_turns :]):
            answer = self._compact_text(turn.answer, 900)
            entry: dict[str, Any] = {
                "turn_index": turn.turn_index,
                "question": self._compact_text(turn.question, 500),
                "resolved_question": self._compact_text(turn.resolved_question, 500),
                "answer": answer,
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

    def _looks_like_follow_up(self, question: str) -> bool:
        lowered = question.casefold()
        if any(lowered.startswith(prefix) for prefix in _FOLLOW_UP_PREFIXES):
            return True
        words = _words(question)
        if not words:
            return False
        if len(words) <= 8 and words[0] in {"why", "how"}:
            return True
        if len(words) <= 10 and _REFERENCE_TERMS.intersection(words):
            return True
        return False

    @staticmethod
    def _compact_text(text: str, limit: int) -> str:
        cleaned = _clean(text)
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1].rstrip() + "…"
