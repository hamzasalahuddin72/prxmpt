from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from clearcue.intelligence.prompt_builder import SYSTEM_INSTRUCTIONS
from clearcue.intelligence.retriever import RetrievedChunk, tokenize


class ProviderError(RuntimeError):
    pass


class AnswerProvider(Protocol):
    def generate(self, prompt: str) -> str: ...


@dataclass(slots=True)
class OpenAIProvider:
    api_key: str
    model: str

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ProviderError("Add an OpenAI API key in Settings first.")
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            response = client.responses.create(
                model=self.model,
                instructions=SYSTEM_INSTRUCTIONS,
                input=prompt,
            )
            answer = (response.output_text or "").strip()
            if not answer:
                raise ProviderError("The provider returned an empty answer.")
            return answer
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc


@dataclass(slots=True)
class OllamaProvider:
    base_url: str
    model: str

    def generate(self, prompt: str) -> str:
        endpoint = self.base_url.rstrip("/") + "/api/generate"
        payload = json.dumps(
            {
                "model": self.model,
                "system": SYSTEM_INSTRUCTIONS,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, ValueError) as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc
        answer = str(result.get("response", "")).strip()
        if not answer:
            raise ProviderError("Ollama returned an empty answer.")
        return answer


class LocalOutlineProvider:
    """A deterministic fallback that never sends context over the network."""

    def __init__(self, question: str, context: list[RetrievedChunk]) -> None:
        self.question = question
        self.context = context

    def generate(self, prompt: str) -> str:  # noqa: ARG002 - common provider API
        if not self.context:
            return (
                "I need more personal context to build a grounded answer. Add your CV, the job "
                "description, project notes or a STAR example in Context, then try again."
            )
        keywords = set(tokenize(self.question))
        candidates: list[tuple[int, str]] = []
        for item in self.context:
            sentences = re.split(r"(?<=[.!?])\s+", item.content)
            for sentence in sentences:
                score = len(keywords.intersection(tokenize(sentence)))
                if score and 25 <= len(sentence) <= 320:
                    candidates.append((score, sentence.strip()))
        selected: list[str] = []
        for _, sentence in sorted(candidates, reverse=True):
            if sentence not in selected:
                selected.append(sentence)
            if len(selected) == 3:
                break
        if not selected:
            selected = [self.context[0].content[:320].strip()]
        bullets = "\n".join(f"• {sentence}" for sentence in selected)
        return (
            "Local grounded outline — turn these verified points into your own spoken answer:\n\n"
            f"{bullets}\n\n"
            "Suggested structure: give a direct opening, explain your strongest relevant example, "
            "then finish with the result or what you learned."
        )

