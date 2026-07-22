from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass


STOP_WORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "been", "by", "can", "did",
    "do", "for", "from", "had", "has", "have", "how", "i", "in", "is", "it",
    "me", "my", "of", "on", "or", "that", "the", "their", "this", "to", "was",
    "were", "what", "when", "where", "which", "who", "why", "will", "with", "you",
    "your",
}

# These words are useful to a broad retrieval query, but they cannot safely
# identify one subject within a multi-topic profile or meeting record.  A
# locked-topic lookup must use distinctive evidence instead: a project name,
# person, organisation, product, domain term, or similarly uncommon detail.
LOCKED_TOPIC_GENERIC_TERMS = STOP_WORDS | {
    "answer",
    "application",
    "approach",
    "background",
    "build",
    "built",
    "business",
    "code",
    "company",
    "contribution",
    "data",
    "database",
    "deliver",
    "delivered",
    "development",
    "developer",
    "experience",
    "feature",
    "git",
    "github",
    "goal",
    "help",
    "improve",
    "implementation",
    "interview",
    "job",
    "javascript",
    "meeting",
    "outcome",
    "php",
    "process",
    "product",
    "project",
    "question",
    "result",
    "role",
    "software",
    "system",
    "team",
    "technology",
    "time",
    "use",
    "used",
    "using",
    "website",
    "work",
    "worked",
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
    tokens = (
        token.strip(".")
        for token in re.findall(r"[a-z0-9+#.]{2,}", text.lower())
    )
    return [token for token in tokens if len(token) >= 2 and token not in STOP_WORDS]


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

    def retrieve_locked(self, topic_context: str, limit: int = 5) -> list[RetrievedChunk]:
        """Return evidence that belongs to an already locked conversation topic.

        Regular retrieval favours useful context for a fresh question.  That is
        intentionally permissive: a broad question such as "tell me about your
        experience" benefits from more than one profile section.  It is unsafe
        for a follow-up that has already been linked to one topic.  Common terms
        like "team", "PHP", or "database" can otherwise retrieve facts from a
        different project which happens to use the same technology.

        A locked lookup therefore has no fallback and requires each returned
        chunk to contain at least one distinctive topic anchor.  When none can
        be proven, the caller receives an empty evidence list and can rely on
        the locked conversation facts instead of silently widening scope.
        """

        if not self.chunks:
            return []
        topic_tokens = Counter(tokenize(topic_context))
        anchors = self._locked_topic_anchors(topic_tokens)
        if not anchors:
            return []

        total = len(self.chunks)
        scored: list[RetrievedChunk] = []
        for (title, content), chunk_tokens in zip(self.chunks, self._tokens, strict=True):
            matched_anchors = set(chunk_tokens).intersection(anchors)
            if not matched_anchors:
                continue
            length_normaliser = 1.0 + math.log1p(sum(chunk_tokens.values()))
            relevance = self._score_tokens(topic_tokens, chunk_tokens)
            anchor_score = sum(
                anchors[token] * (1 + math.log(chunk_tokens[token]))
                for token in matched_anchors
            )
            # The anchor score deliberately dominates broad lexical overlap.
            # This keeps a follow-up in the topic whose distinctive evidence is
            # present, even when another chunk shares several generic skills.
            score = (relevance + (anchor_score * 3.0)) / length_normaliser
            focused = self._focused_content(content, matched_anchors)
            scored.append(RetrievedChunk(title, focused, score))
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

    def _locked_topic_anchors(self, topic_tokens: Counter[str]) -> dict[str, float]:
        """Find distinctive terms from locked context which are present in sources."""

        total = len(self.chunks)
        # Terms in more than half of the available chunks are too broad to act
        # as a hard boundary.  One-chunk profiles still work because passage
        # focusing below limits the evidence to sentences with the topic term.
        max_document_frequency = max(1, math.ceil(total / 2))
        anchors: dict[str, float] = {}
        for token in topic_tokens:
            frequency = self._document_frequency.get(token, 0)
            if (
                not frequency
                or frequency > max_document_frequency
                or token in LOCKED_TOPIC_GENERIC_TERMS
            ):
                continue
            inverse_frequency = math.log((total + 1) / (frequency + 1)) + 1
            anchors[token] = inverse_frequency
        return anchors

    def _score_tokens(
        self,
        query_tokens: Counter[str],
        chunk_tokens: Counter[str],
    ) -> float:
        total = len(self.chunks)
        score = 0.0
        for token, query_count in query_tokens.items():
            frequency = chunk_tokens.get(token, 0)
            if not frequency:
                continue
            inverse_frequency = math.log((total + 1) / (self._document_frequency[token] + 1)) + 1
            score += query_count * (1 + math.log(frequency)) * inverse_frequency
        return score

    @staticmethod
    def _focused_content(content: str, anchors: set[str]) -> str:
        """Keep a matched source passage from leaking adjacent, unrelated facts.

        Uploaded documents are normally chunked by word count and a chunk can
        straddle two CV entries or meeting topics.  Keeping only sentences that
        contain a proven anchor gives the provider a narrow evidence block.  We
        retain the full chunk only for unpunctuated input, where a sentence-level
        boundary cannot be established safely.
        """

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", content)
            if sentence.strip()
        ]
        if len(sentences) < 2:
            return content.strip()
        focused = [
            sentence
            for sentence in sentences
            if anchors.intersection(tokenize(sentence))
        ]
        return " ".join(focused) if focused else content.strip()

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
