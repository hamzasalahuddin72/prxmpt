from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any


# These are conversation behaviours rather than interview-specific words. They
# cover a user asking for the next detail of a topic in a meeting, a tutorial,
# a planning conversation, or an interview.
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
        "one",
        "ones",
    }
)

_CONTINUATION_PREFIXES = (
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

_DETAIL_TERMS = frozenset(
    {
        "action",
        "approach",
        "architecture",
        "challenge",
        "contribution",
        "database",
        "decision",
        "detail",
        "implementation",
        "method",
        "outcome",
        "process",
        "reason",
        "responsibility",
        "result",
        "role",
        "stack",
        "technology",
        "tech",
        "timeline",
        "tool",
        "tradeoff",
        "tradeoffs",
        "why",
    }
)

_TECHNICAL_TERMS = frozenset(
    {
        "api",
        "application",
        "backend",
        "code",
        "database",
        "frontend",
        "git",
        "javascript",
        "mysql",
        "php",
        "python",
        "rapidapi",
        "software",
        "sql",
        "stack",
        "technology",
        "website",
    }
)

_NEW_TOPIC_MARKERS = (
    "on a different topic",
    "on another topic",
    "let's move on",
    "lets move on",
    "switching topics",
    "new topic",
    "separately",
)

_DANGLING_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "at",
        "for",
        "from",
        "in",
        "of",
        "or",
        "the",
        "to",
        "with",
    }
)

# A small, extensible ASR lexicon. Each repair still requires evidence from the
# active topic; it is never used as an unconditional rewrite of a transcript.
_ASR_REPAIRS = (
    ("text tag", "tech stack", "technical"),
    ("test stack", "tech stack", "technical"),
    ("data base", "database", "technical"),
    ("source cord", "source code", "technical"),
    ("get hub", "GitHub", "technical"),
    ("java script", "JavaScript", "technical"),
)

_STOP_WORDS = frozenset(
    {
        "a",
        "about",
        "an",
        "and",
        "are",
        "can",
        "could",
        "did",
        "do",
        "does",
        "for",
        "have",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "more",
        "of",
        "or",
        "tell",
        "that",
        "the",
        "this",
        "to",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#.']+", text.casefold())


def meaningful_words(text: str) -> set[str]:
    return {word for word in words(text) if word not in _STOP_WORDS and len(word) > 1}


@dataclass(frozen=True, slots=True)
class GateDecision:
    """A deterministic, provider-neutral decision for one spoken question."""

    raw_question: str
    resolved_question: str
    status: str
    reason: str
    is_follow_up: bool
    parent_turn_index: int | None
    topic_lock_turn_index: int | None
    follow_up_score: float
    repair_confidence: float
    clarification_message: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_answerable(self) -> bool:
        return self.status in {
            "accepted_new_topic",
            "accepted_follow_up",
            "repaired_follow_up",
        }


class ConversationGate:
    """Resolve conversational continuity before an answer provider is called.

    This deliberately uses transparent scoring rather than a hidden model. It
    is fast enough for live speech, works offline, and can be tuned from saved
    gate metadata when real-world transcripts expose a false decision.
    """

    FOLLOW_UP_THRESHOLD = 0.38

    def evaluate(self, question: str, turns: Iterable[object]) -> GateDecision:
        raw = clean_text(question)
        if not raw:
            raise ValueError("Question cannot be empty")
        previous = tuple(turns)
        parent, follow_up_score, score_parts = self._best_parent(raw, previous)
        is_follow_up = parent is not None and follow_up_score >= self.FOLLOW_UP_THRESHOLD
        parent_index = self._turn_index(parent) if is_follow_up else None
        topic_lock_index = self._topic_lock_index(parent) if is_follow_up else None
        if is_follow_up and topic_lock_index is None:
            topic_lock_index = parent_index

        repaired, repair_confidence, repair_reason = self._repair(
            raw,
            parent if is_follow_up else None,
        )
        resolved = repaired or raw
        ambiguity_reason = self._ambiguity_reason(resolved, raw, repaired)
        metadata = {
            "decision_version": 1,
            "follow_up_score": round(follow_up_score, 3),
            "follow_up_signals": score_parts,
            "repair_confidence": round(repair_confidence, 3),
            "repair_reason": repair_reason,
            "topic_lock_turn_index": topic_lock_index,
        }

        if ambiguity_reason:
            return GateDecision(
                raw_question=raw,
                resolved_question=resolved,
                status="clarification_needed",
                reason=ambiguity_reason,
                is_follow_up=is_follow_up,
                parent_turn_index=parent_index,
                topic_lock_turn_index=topic_lock_index,
                follow_up_score=follow_up_score,
                repair_confidence=repair_confidence,
                clarification_message=(
                    "I caught part of that, but the question is unclear. "
                    "Could you repeat or rephrase it?"
                ),
                metadata=metadata,
            )

        if repaired and is_follow_up:
            status = "repaired_follow_up"
            reason = repair_reason or "high-confidence contextual transcription repair"
        elif is_follow_up:
            status = "accepted_follow_up"
            reason = "continuation signals matched the active conversation topic"
        else:
            status = "accepted_new_topic"
            reason = "clear standalone question with no confident parent turn"
        return GateDecision(
            raw_question=raw,
            resolved_question=resolved,
            status=status,
            reason=reason,
            is_follow_up=is_follow_up,
            parent_turn_index=parent_index,
            topic_lock_turn_index=topic_lock_index,
            follow_up_score=follow_up_score,
            repair_confidence=repair_confidence,
            metadata=metadata,
        )

    def _best_parent(
        self,
        question: str,
        turns: tuple[object, ...],
    ) -> tuple[object | None, float, dict[str, float]]:
        if not turns:
            return None, 0.0, {}
        best_turn: object | None = None
        best_score = 0.0
        best_parts: dict[str, float] = {}
        for position, turn in enumerate(reversed(turns[-6:]), start=1):
            score, parts = self._follow_up_score(question, turn, position)
            if score > best_score:
                best_turn = turn
                best_score = score
                best_parts = parts
        return best_turn, min(1.0, best_score), best_parts

    def _follow_up_score(
        self,
        question: str,
        turn: object,
        recency_position: int,
    ) -> tuple[float, dict[str, float]]:
        lowered = question.casefold()
        question_words = words(question)
        previous_text = " ".join(
            str(getattr(turn, field, "") or "")
            for field in ("question", "resolved_question", "answer")
        )
        previous_words = meaningful_words(previous_text)
        question_terms = meaningful_words(question)
        parts: dict[str, float] = {}

        references = len(_REFERENCE_TERMS.intersection(question_words))
        if references:
            parts["reference"] = min(0.34, 0.18 + 0.08 * references)
        if any(lowered.startswith(prefix) for prefix in _CONTINUATION_PREFIXES):
            parts["continuation_prefix"] = 0.28
        if len(question_words) <= 10:
            parts["short_question"] = 0.14
        detail_terms = _DETAIL_TERMS.intersection(question_terms)
        if detail_terms:
            parts["detail_request"] = min(0.26, 0.16 + 0.05 * len(detail_terms))
        shared_terms = question_terms.intersection(previous_words)
        if shared_terms:
            parts["topic_overlap"] = min(0.24, 0.08 * len(shared_terms))
        if (
            _TECHNICAL_TERMS.intersection(question_terms)
            and _TECHNICAL_TERMS.intersection(previous_words)
        ):
            parts["technical_topic_match"] = 0.20
        if _TECHNICAL_TERMS.intersection(previous_words):
            for alias, _replacement, category in _ASR_REPAIRS:
                if category == "technical" and re.search(
                    rf"\b{re.escape(alias)}\b",
                    question,
                    re.IGNORECASE,
                ):
                    # A recognised noisy phrase is not enough to rewrite on
                    # its own, but it is strong evidence that this question is
                    # continuing a technical topic rather than starting a new
                    # subject.
                    parts["contextual_repair_candidate"] = 0.42
                    break
        if recency_position == 1:
            parts["recency"] = 0.05
        elif recency_position == 2:
            parts["recency"] = 0.02
        if any(marker in lowered for marker in _NEW_TOPIC_MARKERS):
            parts["new_topic_penalty"] = -0.60

        # A long question with a fresh set of content terms is normally a new
        # subject, even if it happens immediately after another answer.
        if len(question_words) >= 10 and question_terms and not shared_terms:
            if not _REFERENCE_TERMS.intersection(question_words):
                parts["fresh_topic_penalty"] = -0.18
        return sum(parts.values()), parts

    @staticmethod
    def _turn_index(turn: object | None) -> int | None:
        value = getattr(turn, "turn_index", None)
        return int(value) if isinstance(value, int) else None

    @staticmethod
    def _topic_lock_index(turn: object | None) -> int | None:
        value = getattr(turn, "topic_lock_turn_index", None)
        return int(value) if isinstance(value, int) else None

    def _repair(
        self,
        question: str,
        parent: object | None,
    ) -> tuple[str | None, float, str]:
        if parent is None:
            return None, 0.0, ""
        parent_text = " ".join(
            str(getattr(parent, field, "") or "")
            for field in ("question", "resolved_question", "answer")
        )
        parent_terms = meaningful_words(parent_text)
        technical_context = bool(_TECHNICAL_TERMS.intersection(parent_terms))
        for alias, replacement, category in _ASR_REPAIRS:
            pattern = re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)
            if not pattern.search(question):
                continue
            if category == "technical" and not technical_context:
                return None, 0.0, "ASR-like phrase lacks supporting active-topic evidence"
            candidate = pattern.sub(replacement, question)
            # The explicit alias match is the main signal. The string score
            # protects future broader aliases from becoming silent rewrites.
            similarity = SequenceMatcher(
                None,
                question.casefold(),
                candidate.casefold(),
            ).ratio()
            confidence = min(0.98, 0.88 + similarity * 0.10)
            if confidence >= 0.92:
                return (
                    candidate,
                    confidence,
                    f"context-supported ASR repair: '{alias}' → '{replacement}'",
                )
        return None, 0.0, ""

    @staticmethod
    def _ambiguity_reason(
        resolved: str,
        raw: str,
        repaired: str | None,
    ) -> str:
        tokens = words(resolved)
        if len(tokens) < 3:
            return "question is too short to identify a reliable intent"
        if tokens and tokens[-1] in _DANGLING_WORDS:
            return "question ends with an unfinished phrase"
        connector_count = sum(token in {"for", "to", "of", "with"} for token in tokens)
        if len(tokens) >= 8 and connector_count >= 3:
            return "question contains repeated connector phrases and no safe reconstruction"
        if re.search(r"\bfor\s+the\s+\w+\s+for\s+the\b", resolved, re.IGNORECASE):
            return "question appears grammatically fragmented"
        if not repaired:
            for alias, _replacement, _category in _ASR_REPAIRS:
                if re.search(rf"\b{re.escape(alias)}\b", raw, re.IGNORECASE):
                    return "possible transcription error needs more context before repair"
        return ""
