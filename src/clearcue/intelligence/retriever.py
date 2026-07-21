from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "can", "did",
    "do", "for", "from", "had", "has", "have", "how", "i", "in", "is", "it",
    "me", "my", "of", "on", "or", "that", "the", "their", "this", "to", "was",
    "were", "what", "when", "where", "which", "who", "why", "will", "with", "you",
    "your",
}

INTENT_EXPANSIONS = (
    (
        ("tell me about yourself", "introduce yourself", "background"),
        ("experience", "education", "skills", "projects", "career", "profile"),
    ),
    (
        ("why this role", "why do you want", "why are you interested", "opportunity"),
        ("experience", "skills", "career", "goals", "role", "responsibilities"),
    ),
    (
        ("career change", "current field", "change fields", "changing careers"),
        ("education", "experience", "career", "skills", "transferable", "goals"),
    ),
    (
        ("strength", "weakness", "proud", "achievement", "challenge"),
        ("experience", "skills", "projects", "achievement", "result"),
    ),
)


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9+#.]{2,}", text.lower())
        if token not in STOP_WORDS
    ]


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    title: str
    content: str
    score: float


class ContextRetriever:
    def __init__(self, chunks: list[tuple[str, str]]) -> None:
        self.chunks = chunks
        self._tokens = [Counter(tokenize(content)) for _, content in chunks]
        self._document_frequency: Counter[str] = Counter()
        for tokens in self._tokens:
            self._document_frequency.update(tokens.keys())

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        *,
        allow_fallback: bool = True,
    ) -> list[RetrievedChunk]:
        query_tokens = Counter(tokenize(query))
        if not self.chunks or not query_tokens:
            return []
        lowered_query = query.lower()
        for markers, expansion in INTENT_EXPANSIONS:
            if any(marker in lowered_query for marker in markers):
                query_tokens.update(expansion)
        total = len(self.chunks)
        scored: list[RetrievedChunk] = []
        for (title, content), chunk_tokens in zip(self.chunks, self._tokens, strict=True):
            score = 0.0
            length_normaliser = 1.0 + math.log1p(sum(chunk_tokens.values()))
            for token, query_count in query_tokens.items():
                frequency = chunk_tokens.get(token, 0)
                if not frequency:
                    continue
                inverse_frequency = math.log((total + 1) / (self._document_frequency[token] + 1)) + 1
                score += query_count * (1 + math.log(frequency)) * inverse_frequency
            lowered = content.lower()
            meaningful_query = " ".join(query_tokens.keys())
            if meaningful_query and meaningful_query in lowered:
                score += 3.0
            if score > 0:
                scored.append(RetrievedChunk(title, content, score / length_normaliser))
        ranked = sorted(scored, key=lambda item: item.score, reverse=True)

        # Broad interview questions often share few literal words with a CV.
        # Supplement sparse lexical matches with a small, deterministic sample
        # of the profile rather than telling the model no context exists.
        if not allow_fallback:
            return ranked[:limit]
        target = min(limit, min(3, total))
        selected = ranked[:limit]
        selected_keys = {(item.title, item.content) for item in selected}
        if len(selected) < target:
            fallback = sorted(
                self.chunks,
                key=lambda item: self._fallback_priority(item[0], lowered_query),
            )
            for title, content in fallback:
                key = (title, content)
                if key in selected_keys:
                    continue
                selected.append(RetrievedChunk(title, content, 0.0))
                selected_keys.add(key)
                if len(selected) >= target:
                    break
        return selected[:limit]

    @staticmethod
    def _fallback_priority(title: str, query: str) -> tuple[int, str]:
        lowered = title.lower()
        wants_role = any(
            marker in query
            for marker in ("role", "organisation", "organization", "company", "opportunity")
        )
        if wants_role and any(marker in lowered for marker in ("job", "role", "description")):
            rank = 0
        elif any(marker in lowered for marker in ("cv", "resume", "résumé", "profile")):
            rank = 1
        elif any(marker in lowered for marker in ("job", "role", "description")):
            rank = 2
        else:
            rank = 3
        return rank, lowered
