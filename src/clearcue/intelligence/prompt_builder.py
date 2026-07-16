from __future__ import annotations

from clearcue.intelligence.retriever import RetrievedChunk


SYSTEM_INSTRUCTIONS = """You are ClearCue, an interview practice and disclosed meeting coach.
Produce a natural first-person answer that the user can adapt and speak.

Grounding rules:
- Use only facts present in the supplied context.
- Never invent employers, dates, metrics, qualifications, technologies or achievements.
- If the context is insufficient, explicitly say what information is missing.
- Answer the question directly before adding detail.
- Use STAR structure only when the question calls for a behavioural example.
- Keep the language natural, specific and easy to say aloud.
- Do not claim to have personally completed work unless the context supports it.
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
) -> str:
    style_rule = STYLE_RULES.get(style, STYLE_RULES["concise"])
    if context:
        context_text = "\n\n".join(
            f"SOURCE: {item.title}\n{item.content}" for item in context
        )
    else:
        context_text = "No relevant personal context was found."
    return (
        f"QUESTION\n{question.strip()}\n\n"
        f"ANSWER STYLE\n{style_rule}\n\n"
        f"USER CONTEXT\n{context_text}\n\n"
        "Return only the suggested answer."
    )

