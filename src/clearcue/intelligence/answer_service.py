from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from clearcue.config import AppConfig
from clearcue.intelligence.prompt_builder import build_prompt
from clearcue.intelligence.providers import (
    GeminiProvider,
    LocalOutlineProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderError,
)
from clearcue.intelligence.retriever import ContextRetriever, RetrievedChunk
from clearcue.security import SecretStoreError, get_gemini_key, get_openai_key


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
        cleaned, context, prompt = self._prepare(question, style)
        answer = self._provider(cleaned, context).generate(prompt)
        return self._result(cleaned, answer, context)

    def generate_stream(
        self,
        question: str,
        style: str | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> AnswerResult:
        """Generate an answer while forwarding provider text deltas when available."""

        cleaned, context, prompt = self._prepare(question, style)
        provider = self._provider(cleaned, context)
        stream = getattr(provider, "generate_stream", None)
        if callable(stream):
            chunks: list[str] = []
            for chunk in stream(prompt):
                if not chunk:
                    continue
                chunks.append(chunk)
                if on_delta:
                    on_delta(chunk)
            answer = "".join(chunks).strip()
        else:
            answer = provider.generate(prompt).strip()
            if answer and on_delta:
                on_delta(answer)
        if not answer:
            raise ProviderError("The provider returned an empty answer.")
        return self._result(cleaned, answer, context)

    def _prepare(
        self,
        question: str,
        style: str | None,
    ) -> tuple[str, list[RetrievedChunk], str]:
        cleaned = " ".join(question.split())
        if not cleaned:
            raise ValueError("Enter or detect a question first.")
        context = self.retriever.retrieve(cleaned, limit=5)
        prompt = build_prompt(cleaned, context, style or self.config.answer_style)
        return cleaned, context, prompt

    @staticmethod
    def _result(
        cleaned: str,
        answer: str,
        context: list[RetrievedChunk],
    ) -> AnswerResult:
        sources = tuple(dict.fromkeys(item.title for item in context))
        return AnswerResult(cleaned, answer.strip(), sources)

    def _provider(self, question: str, context: list[RetrievedChunk]):
        if self.config.answer_provider == "gemini":
            try:
                key = get_gemini_key()
            except SecretStoreError as exc:
                raise ProviderError(str(exc)) from exc
            return GeminiProvider(key, self.config.gemini_model)
        if self.config.answer_provider == "openai":
            try:
                key = get_openai_key()
            except SecretStoreError as exc:
                raise ProviderError(str(exc)) from exc
            return OpenAIProvider(key, self.config.openai_model)
        if self.config.answer_provider == "ollama":
            return OllamaProvider(self.config.ollama_url, self.config.ollama_model)
        return LocalOutlineProvider(question, context)
