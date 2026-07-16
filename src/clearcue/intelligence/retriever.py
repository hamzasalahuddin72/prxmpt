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

    def retrieve(self, query: str, limit: int = 5) -> list[RetrievedChunk]:
        query_tokens = Counter(tokenize(query))
        if not self.chunks or not query_tokens:
            return []
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
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

