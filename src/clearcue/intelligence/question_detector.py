from __future__ import annotations

import re
from dataclasses import dataclass


QUESTION_OPENERS = (
    "what ",
    "why ",
    "when ",
    "where ",
    "who ",
    "which ",
    "how ",
    "can you ",
    "could you ",
    "would you ",
    "will you ",
    "do you ",
    "did you ",
    "have you ",
    "are you ",
    "were you ",
    "tell me ",
    "talk me through ",
    "describe ",
    "explain ",
    "give me an example ",
)

QUESTION_START_WORDS = frozenset(
    opener.strip().split()[0] for opener in QUESTION_OPENERS
)

EMBEDDED_PROMPTS = (
    "tell me about",
    "walk me through",
    "talk me through",
    "give an example",
    "your experience with",
    "your approach to",
)

DECLARATIVE_REMARK_OPENERS = (
    "what a ",
    "what an ",
    "how nice ",
    "how great ",
    "how interesting ",
)

PREMISE_MARKERS = (
    "given that",
    "considering",
    "because you",
    "since you",
    "as you",
    "you mentioned",
)

INCOMPLETE_ENDINGS = (
    " and",
    " or",
    " versus",
    " because",
    " if",
    " when",
    " with",
    " about",
    " to",
)


@dataclass(frozen=True, slots=True)
class _QuestionMatch:
    fragment: str
    start: int
    end: int
    clause_index: int
    score: float


def clean_transcript(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\b(\w+)\s+\1\b", r"\1", cleaned, flags=re.IGNORECASE)
    return cleaned.strip("-–— ")


def _clauses(text: str) -> list[tuple[str, int, int]]:
    return [
        (match.group(0).strip(), match.start(), match.end())
        for match in re.finditer(r"[^.!?]+(?:[.!?]+|$)", text)
        if match.group(0).strip()
    ]


def _fragment_in_clause(clause: str) -> tuple[str, int] | None:
    lowered = clause.lower().lstrip()
    leading = len(clause) - len(clause.lstrip())
    matches: list[tuple[int, str]] = []
    for opener in QUESTION_OPENERS:
        position = lowered.find(opener)
        if position >= 0:
            matches.append((position, opener))
    for phrase in EMBEDDED_PROMPTS:
        position = lowered.find(phrase)
        if position >= 0:
            matches.append((position, phrase))
    if matches:
        position, _ = min(matches, key=lambda item: item[0])
        return clause[leading + position :].strip(), leading + position
    if clause.rstrip().endswith("?"):
        return clause.strip(), leading
    return None


def _question_matches(text: str) -> list[_QuestionMatch]:
    clauses = _clauses(text)
    matches: list[_QuestionMatch] = []
    total = max(1, len(clauses))
    for index, (clause, clause_start, _clause_end) in enumerate(clauses):
        extracted = _fragment_in_clause(clause)
        if extracted is None:
            continue
        fragment, offset = extracted
        lowered = fragment.lower()
        score = min(len(fragment), 140) / 7.0
        if any(lowered.startswith(opener) for opener in QUESTION_OPENERS):
            score += 35.0
        if fragment.rstrip().endswith("?"):
            score += 32.0
        if any(phrase in lowered for phrase in EMBEDDED_PROMPTS):
            score += 12.0
        score += (index / total) * 8.0
        start = clause_start + offset
        matches.append(
            _QuestionMatch(
                fragment=fragment,
                start=start,
                end=start + len(fragment),
                clause_index=index,
                score=score,
            )
        )
    return matches


def _best_question_match(text: str) -> _QuestionMatch | None:
    matches = _question_matches(text)
    if not matches:
        return None
    return max(matches, key=lambda item: (item.score, item.start))


def question_fragment(text: str) -> str | None:
    """Return the strongest exact question span from a noisy utterance."""

    cleaned = clean_transcript(text)
    match = _best_question_match(cleaned)
    return match.fragment if match else None


def potential_question_candidate(text: str) -> str | None:
    """Return the question-like trailing sentence while it is still forming."""

    cleaned = clean_transcript(text)
    if not cleaned:
        return None

    clauses = _clauses(cleaned)
    candidate = clauses[-1][0] if clauses else cleaned
    lowered = candidate.lower()
    first_word = lowered.split(maxsplit=1)[0].rstrip("?!.,:;")
    if first_word in QUESTION_START_WORDS:
        return candidate
    if candidate.endswith("?"):
        return candidate

    matches = [
        (lowered.rfind(phrase), phrase)
        for phrase in EMBEDDED_PROMPTS
        if phrase in lowered
    ]
    if matches:
        start, _ = max(matches)
        return candidate[start:].strip()
    return None


def _normalise_piece(text: str) -> str:
    piece = clean_transcript(text).strip(" .?!,;:")
    piece = re.sub(r"\bif\s+if\b", "if", piece, flags=re.IGNORECASE)
    return piece


def _premise_and_condition(
    cleaned: str,
    question_match: _QuestionMatch,
) -> tuple[str, str]:
    clauses = _clauses(cleaned)
    earlier = clauses[: question_match.clause_index]
    premise = ""
    condition = ""

    for clause, _start, _end in reversed(earlier):
        if _fragment_in_clause(clause) is not None:
            continue
        lowered = clause.lower()
        marker_positions = [lowered.find(marker) for marker in PREMISE_MARKERS]
        marker_positions = [position for position in marker_positions if position >= 0]
        if marker_positions:
            premise = _normalise_piece(clause[min(marker_positions) :])
            break

    for clause, _start, _end in reversed(earlier):
        if _fragment_in_clause(clause) is not None:
            continue
        lowered = clause.lower()
        if "position becomes available" in lowered:
            start = lowered.find("position becomes available")
            condition = "If a " + _normalise_piece(clause[start:])
            break
        conditional = re.search(r"\b(if|when|should)\b", lowered)
        if conditional:
            condition = _normalise_piece(clause[conditional.start() :])
            break

    # A later ASR pass often restates a condition more accurately. Keep the
    # premise but replace its older embedded condition with the later version.
    if premise and condition:
        premise = re.split(r",?\s+if\b", premise, maxsplit=1, flags=re.IGNORECASE)[0]
        premise = premise.strip(" ,")
    return premise, condition


def _reconstruct_question(cleaned: str, match: _QuestionMatch) -> str:
    fragment = _normalise_piece(match.fragment)
    premise, condition = _premise_and_condition(cleaned, match)
    pieces = [piece for piece in (premise, condition) if piece]
    if pieces:
        pieces = [
            piece if index == 0 else piece[:1].lower() + piece[1:]
            for index, piece in enumerate(pieces)
        ]
        fragment = fragment[:1].lower() + fragment[1:]
        reconstructed = ", ".join([*pieces, fragment])
    else:
        reconstructed = fragment

    tail = cleaned[match.end :].lower()
    if "now" in tail and "future" in tail:
        reconstructed = reconstructed.rstrip(" .?!") + ", both now and in the future"
    reconstructed = reconstructed.strip()
    if reconstructed:
        reconstructed = reconstructed[:1].upper() + reconstructed[1:]
    return reconstructed.rstrip(" .?!") + "?"


def detect_question(text: str) -> str | None:
    """Return the strongest complete interview question in a noisy utterance."""

    cleaned = clean_transcript(text)
    if not cleaned:
        return None
    match = _best_question_match(cleaned)
    if match is None or len(match.fragment) < 8:
        return None
    lowered = match.fragment.lower()
    if match.fragment.endswith((".", "!")) and lowered.startswith(
        DECLARATIVE_REMARK_OPENERS
    ):
        return None
    opener = any(lowered.startswith(prefix) for prefix in QUESTION_OPENERS)
    question_mark = match.fragment.rstrip().endswith("?")
    embedded_prompt = any(phrase in lowered for phrase in EMBEDDED_PROMPTS)
    if not (opener or question_mark or embedded_prompt):
        return None
    unfinished = _normalise_piece(match.fragment).lower().endswith(INCOMPLETE_ENDINGS)
    if unfinished and not question_mark:
        return None
    return _reconstruct_question(cleaned, match)
