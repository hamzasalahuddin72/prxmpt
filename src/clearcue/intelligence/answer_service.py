from __future__ import annotations

from dataclasses import dataclass

from clearcue.config import AppConfig
from clearcue.intelligence.prompt_builder import build_prompt
from clearcue.intelligence.providers import (
    LocalOutlineProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderError,
)
from clearcue.intelligence.retriever import ContextRetriever, RetrievedChunk
from clearcue.security import SecretStoreError, get_openai_key


@dataclass(frozen=True, slots=True)
class AnswerResult:
    question: str
    answer: str
    sources: tuple[str, ...]


class AnswerService:
    def __init__(self, config: AppConfig, chunks: list[tuple[str, str]]) -> None:
        self.config = config
        self.retriever = ContextRetriever(chunks)

    def generate(self, question: str, style: str | None = None) -> AnswerResult:
        cleaned = " ".join(question.split())
        if not cleaned:
            raise ValueError("Enter or detect a question first.")
        context = self.retriever.retrieve(cleaned, limit=5)
        prompt = build_prompt(cleaned, context, style or self.config.answer_style)
        provider = self._provider(cleaned, context)
        answer = provider.generate(prompt)
        sources = tuple(dict.fromkeys(item.title for item in context))
        return AnswerResult(cleaned, answer, sources)

    def _provider(self, question: str, context: list[RetrievedChunk]):
        if self.config.answer_provider == "openai":
            try:
                key = get_openai_key()
            except SecretStoreError as exc:
                raise ProviderError(str(exc)) from exc
            return OpenAIProvider(key, self.config.openai_model)
        if self.config.answer_provider == "ollama":
            return OllamaProvider(self.config.ollama_url, self.config.ollama_model)
        return LocalOutlineProvider(question, context)

