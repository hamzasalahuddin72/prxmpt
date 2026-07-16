from __future__ import annotations

import re


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


def clean_transcript(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned.strip("-–— ")


def detect_question(text: str) -> str | None:
    """Return a cleaned interview question when the utterance looks actionable."""
    cleaned = clean_transcript(text)
    if len(cleaned) < 8:
        return None
    lowered = cleaned.lower()
    opener = any(lowered.startswith(prefix) for prefix in QUESTION_OPENERS)
    question_mark = cleaned.endswith("?")
    embedded_prompt = any(
        phrase in lowered
        for phrase in (
            "tell me about",
            "walk me through",
            "talk me through",
            "give an example",
            "your experience with",
            "your approach to",
        )
    )
    if not (opener or question_mark or embedded_prompt):
        return None
    if cleaned[-1] not in "?.!":
        cleaned += "?"
    return cleaned

