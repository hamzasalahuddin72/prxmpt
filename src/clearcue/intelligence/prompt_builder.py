from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from clearcue.intelligence.retriever import RetrievedChunk


SYSTEM_INSTRUCTIONS = """You are prxmpt, a disclosed conversation, meeting and interview coach.
Produce a natural spoken response that the user can adapt and say aloud.

Grounding rules:
- Use only facts present in the supplied context.
- Never invent employers, dates, metrics, qualifications, technologies or achievements.
- Answer the question directly before adding detail.
- Use STAR structure only when the question calls for a behavioural example.
- Keep the language natural, specific and easy to say aloud.
- Do not claim to have personally completed work unless the context supports it.
- Treat the transcript as potentially noisy: follow the resolved question,
  ignore duplicated phrases and preserve its important premise or trade-off.
- Never output square-bracket placeholders, a template, coaching commentary, or phrases such
  as "I need more information" and "I would need to know".
- If role or organisation details are absent, use verified user experience plus neutral
  wording such as "this role". Do not invent company-specific reasons.
- For a hypothetical choice or trade-off, state a credible decision clearly, then explain the
  criteria, commitment and communication behind it.
- When an active topic lock is present, treat it as a hard evidence boundary.
  Never substitute a similar fact from another project, person, employer or
  discussion topic. If the locked facts do not establish a requested detail,
  state that narrowly and naturally rather than guessing.
- Return only the answer the user could actually say aloud.
"""


STYLE_RULES = {
    "concise": "Aim for 70-120 words and one clear example at most.",
    "detailed": "Aim for 140-220 words, while remaining direct and spoken in tone.",
    "star": "Use Situation, Task, Action and Result, but do not print the STAR labels unless useful.",
    "technical": "Explain the approach, main technical decisions, trade-offs and result in clear language.",
}


def build_prompt(
    question: str,
    context: list[RetrievedChunk],
    style: str = "concise",
    conversation_context: Sequence[Mapping[str, Any]] = (),
) -> str:
    style_rule = STYLE_RULES.get(style, STYLE_RULES["concise"])
    if context:
        context_text = "\n\n".join(
            f"SOURCE: {item.title}\n{item.content}" for item in context
        )
    else:
        context_text = "No relevant personal context was found."
    conversation_text = _conversation_text(conversation_context)
    lock_section = _topic_lock_text(conversation_context, conversation_text)
    conversation_section = lock_section or _rolling_session_text(conversation_text)
    context_heading = (
        "LOCKED VERIFIED EVIDENCE"
        if lock_section
        else "VERIFIED USER CONTEXT"
    )
    return (
        f"RESOLVED QUESTION\n{question.strip()}\n\n"
        f"ANSWER STYLE\n{style_rule}\n\n"
        f"{conversation_section}"
        f"{context_heading}\n{context_text}\n\n"
        "ANSWER REQUIREMENTS\n"
        "Give a direct, confident first-person response. Use concrete facts from the context "
        "when available. Do not mention the context, missing information, placeholders, or "
        "how the answer should be written. Return only the spoken answer."
    )


def _conversation_text(
    conversation_context: Sequence[Mapping[str, Any]],
) -> str:
    entries: list[str] = []
    for item in conversation_context:
        question = str(item.get("resolved_question") or item.get("question") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if not question and not answer:
            continue
        turn_index = str(item.get("turn_index") or "?")
        entries.append(
            f"TURN {turn_index}\nQUESTION: {question}\nANSWER: {answer or '(pending)'}"
        )
    return "\n\n".join(entries)


def _rolling_session_text(conversation_text: str) -> str:
    """Render the compact prior-turn window for non-locked continuations.

    A topic lock uses the stricter ``_topic_lock_text`` path below.  Without a
    lock, the provider still needs the saved, bounded session context to answer
    ordinary referential follow-ups such as ``Why did you choose it?``.
    """

    if not conversation_text:
        return ""
    return (
        "ROLLING SESSION CONTEXT\n"
        "Use this recent conversation only when it helps answer the resolved "
        "question. Prefer the verified user context for independent questions.\n\n"
        f"{conversation_text}\n\n"
    )


def _topic_lock_text(
    conversation_context: Sequence[Mapping[str, Any]],
    conversation_text: str,
) -> str:
    locks = {
        item.get("topic_lock_turn_index")
        for item in conversation_context
        if item.get("topic_lock_turn_index") is not None
    }
    if len(locks) != 1:
        return ""
    lock = next(iter(locks))
    facts = conversation_text or "No prior locked facts were saved."
    return (
        "ACTIVE TOPIC LOCK — HARD EVIDENCE BOUNDARY\n"
        f"Continue only the topic established in turn {lock}. The facts below are "
        "authoritative for this follow-up. Do not use a similar project, person, employer, "
        "meeting subject or source unless the resolved question explicitly changes topic.\n\n"
        f"LOCKED TURN FACTS\n{facts}\n\n"
    )
