from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

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

    def generate(
        self,
        question: str,
        style: str | None = None,
        *,
        conversation_context: Sequence[Mapping[str, Any]] = (),
    ) -> AnswerResult:
        cleaned, context, prompt = self._prepare(
            question,
            style,
            conversation_context,
        )
        answer = self._provider(cleaned, context, conversation_context).generate(prompt)
        return self._result(cleaned, answer, context)

    def generate_stream(
        self,
        question: str,
        style: str | None = None,
        on_delta: Callable[[str], None] | None = None,
        *,
        conversation_context: Sequence[Mapping[str, Any]] = (),
    ) -> AnswerResult:
        """Generate an answer while forwarding provider text deltas when available."""

        cleaned, context, prompt = self._prepare(
            question,
            style,
            conversation_context,
        )
        provider = self._provider(cleaned, context, conversation_context)
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
        conversation_context: Sequence[Mapping[str, Any]],
    ) -> tuple[str, list[RetrievedChunk], str]:
        cleaned = " ".join(question.split())
        if not cleaned:
            raise ValueError("Enter or detect a question first.")
        topic_context = self._locked_topic_context(conversation_context)
        if topic_context:
            # A lock is an evidence boundary, not only an instruction in the
            # prompt.  Do not pass lexically similar facts from another CV
            # project or meeting subject to any provider.
            context = self.retriever.retrieve_locked(topic_context, limit=5)
        else:
            context = self.retriever.retrieve(cleaned, limit=5)
        prompt = build_prompt(
            cleaned,
            context,
            style or self.config.answer_style,
            conversation_context,
        )
        return cleaned, context, prompt

    @staticmethod
    def _locked_topic_context(
        conversation_context: Sequence[Mapping[str, Any]],
    ) -> str:
        lock_values = {
            item.get("topic_lock_turn_index")
            for item in conversation_context
            if item.get("topic_lock_turn_index") is not None
        }
        if len(lock_values) != 1:
            return ""
        lock = next(iter(lock_values))
        locked_parts: list[str] = []
        for item in conversation_context:
            if (
                item.get("turn_index") != lock
                and item.get("topic_lock_turn_index") != lock
            ):
                continue
            locked_parts.extend(
                str(item.get(field) or "")
                for field in ("resolved_question", "question", "answer")
            )
        return " ".join(part.strip() for part in locked_parts if part.strip())

    @staticmethod
    def _result(
        cleaned: str,
        answer: str,
        context: list[RetrievedChunk],
    ) -> AnswerResult:
        sources = tuple(dict.fromkeys(item.title for item in context))
        return AnswerResult(cleaned, answer.strip(), sources)

    def _provider(
        self,
        question: str,
        context: list[RetrievedChunk],
        conversation_context: Sequence[Mapping[str, Any]],
    ):
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
        return LocalOutlineProvider(question, context, conversation_context)
