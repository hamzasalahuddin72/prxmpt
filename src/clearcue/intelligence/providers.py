from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from collections.abc import Iterator
from typing import Any, Protocol

from clearcue.intelligence.prompt_builder import SYSTEM_INSTRUCTIONS
from clearcue.intelligence.retriever import RetrievedChunk, tokenize


class ProviderError(RuntimeError):
    pass


class AnswerProvider(Protocol):
    def generate(self, prompt: str) -> str: ...


def _object_value(value: object, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _gemini_response_text(event: object) -> str:
    """Read text from GenerateContent responses and older SDK event objects."""

    text = _object_value(event, "text")
    if text:
        return str(text)

    delta = _object_value(event, "delta")
    delta_text = _object_value(delta, "text") if delta is not None else None
    return str(delta_text) if delta_text else ""


def _exception_details(exc: Exception) -> str:
    """Flatten a wrapped HTTP exception without exposing request headers or keys."""

    details: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        message = str(current).strip()
        label = current.__class__.__name__
        entry = f"{label}: {message}" if message else label
        if entry not in details:
            details.append(entry)
        current = current.__cause__ or current.__context__
    return " | ".join(details)


def _gemini_connection_failure(exc: Exception) -> bool:
    details = _exception_details(exc).lower()
    markers = (
        "connection error",
        "connecterror",
        "connection refused",
        "connection reset",
        "network is unreachable",
        "network unreachable",
        "name resolution",
        "getaddrinfo",
        "nodename nor servname",
        "proxyerror",
        "proxy error",
        "certificate_verify_failed",
        "sslerror",
        "tls",
    )
    return any(marker in details for marker in markers)


def _proxy_is_configured() -> bool:
    """Detect environment or Windows proxy settings without retaining their values."""

    try:
        return any(
            scheme.lower() in {"http", "https", "all"} and bool(address)
            for scheme, address in urllib.request.getproxies().items()
        )
    except OSError:
        return False


def _gemini_error_message(exc: Exception, *, direct_retry_failed: bool = False) -> str:
    details = _exception_details(exc)
    lowered = details.lower()
    if "429" in lowered or "resource_exhausted" in lowered or "quota" in lowered:
        return (
            "Gemini's current project limit was reached. Wait briefly, check the "
            "AI Studio quota, or switch to Local in Settings."
        )
    if any(marker in lowered for marker in ("401", "403", "api key", "permission_denied")):
        return "Gemini rejected the API key. Create or update it in prxmpt Settings."
    if any(marker in lowered for marker in ("404", "not_found", "model is not found")):
        return (
            "The selected Gemini model is not available to this API key. Choose the Fast "
            "model in Settings, or check model access in Google AI Studio."
        )
    if "failed_precondition" in lowered or "user location is not supported" in lowered:
        return (
            "Gemini is not available from the current region or Google project. Check the "
            "Gemini API supported-regions page or use Local in Settings."
        )
    if "503" in lowered or "unavailable" in lowered:
        return "Gemini is temporarily unavailable. Wait briefly and try again."
    if "timeout" in lowered or "timed out" in lowered:
        return "Gemini did not respond within 45 seconds. Check the connection and try again."
    if any(marker in lowered for marker in ("certificate_verify_failed", "sslerror", "tls")):
        return (
            "Gemini's secure connection could not be verified. Check Windows date/time and "
            "temporarily test without antivirus HTTPS scanning or a corporate TLS proxy."
        )
    if any(
        marker in lowered
        for marker in ("name resolution", "getaddrinfo", "nodename nor servname")
    ):
        return (
            "Gemini's server name could not be resolved. Check DNS, VPN and firewall access "
            "to generativelanguage.googleapis.com, then try again."
        )
    if "proxy" in lowered or direct_retry_failed:
        return (
            "Gemini could not connect through the configured proxy or directly. Check Windows "
            "Proxy/VPN settings and allow generativelanguage.googleapis.com on HTTPS port 443."
        )
    if _gemini_connection_failure(exc):
        return (
            "Gemini could not reach Google's API. Check internet access, VPN/DNS and firewall "
            "access to generativelanguage.googleapis.com on HTTPS port 443."
        )
    return f"Gemini request failed: {details}"


@dataclass(slots=True)
class GeminiProvider:
    api_key: str
    model: str

    def _client(self, *, trust_env: bool = True, timeout_ms: int = 45_000):
        if not self.api_key:
            raise ProviderError("Add a Gemini API key in Settings first.")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ProviderError(
                "Gemini support is missing from this installation. Reinstall prxmpt 1.0.24."
            ) from exc
        try:
            client_args = {} if trust_env else {"trust_env": False}
            return genai.Client(
                api_key=self.api_key.strip(),
                http_options=types.HttpOptions(
                    timeout=timeout_ms,
                    client_args=client_args,
                ),
            )
        except Exception as exc:
            raise ProviderError(_gemini_error_message(exc)) from exc

    def _request_stream(self, prompt: str, *, trust_env: bool) -> Iterator[str]:
        client = self._client(trust_env=trust_env)
        try:
            # GenerateContent is deliberately used here instead of Interactions. prxmpt
            # needs stateless text streaming, and this endpoint has the broadest model,
            # network-proxy and SDK compatibility on installed Windows clients.
            stream = client.models.generate_content_stream(
                model=self.model,
                contents=prompt.strip(),
                config={
                    "system_instruction": SYSTEM_INSTRUCTIONS.strip(),
                    "max_output_tokens": 800,
                },
            )
            for event in stream:
                chunk = _gemini_response_text(event)
                if chunk:
                    yield chunk
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    # A transport cleanup failure must not discard an answer that was
                    # already received successfully.
                    pass

    def _list_models_once(self, *, trust_env: bool) -> list[tuple[str, str]]:
        client = self._client(trust_env=trust_env, timeout_ms=10_000)
        try:
            available: dict[str, str] = {}
            for model in client.models.list():
                actions = (
                    _object_value(model, "supported_actions")
                    or _object_value(model, "supported_generation_methods")
                    or ()
                )
                if "generateContent" not in actions:
                    continue
                name = str(_object_value(model, "name") or "").strip()
                model_id = name.removeprefix("models/")
                lowered = model_id.lower()
                if not model_id or not lowered.startswith(("gemini-", "gemma-")):
                    continue
                if any(
                    marker in lowered
                    for marker in (
                        "audio",
                        "embedding",
                        "image",
                        "live",
                        "robotics",
                        "tts",
                    )
                ):
                    continue
                label = str(
                    _object_value(model, "display_name")
                    or _object_value(model, "displayName")
                    or model_id
                ).strip()
                available[model_id] = label
            return sorted(available.items(), key=lambda item: item[1].casefold())
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    def list_available_models(self) -> list[tuple[str, str]]:
        """Validate this key and list text-generation models without generating."""

        try:
            return self._list_models_once(trust_env=True)
        except ProviderError:
            raise
        except Exception as first_exc:
            if _gemini_connection_failure(first_exc) and _proxy_is_configured():
                try:
                    return self._list_models_once(trust_env=False)
                except ProviderError:
                    raise
                except Exception as direct_exc:
                    raise ProviderError(
                        _gemini_error_message(direct_exc, direct_retry_failed=True)
                    ) from direct_exc
            raise ProviderError(_gemini_error_message(first_exc)) from first_exc

    def generate_stream(self, prompt: str) -> Iterator[str]:
        received = False
        try:
            for chunk in self._request_stream(prompt, trust_env=True):
                received = True
                yield chunk
        except ProviderError:
            raise
        except Exception as first_exc:
            # A stale Windows/environment proxy is a common cause of httpx's opaque
            # "Connection error". If no output has started, safely retry once while
            # bypassing that proxy. We never retry a partially streamed answer.
            if not received and _gemini_connection_failure(first_exc) and _proxy_is_configured():
                try:
                    for chunk in self._request_stream(prompt, trust_env=False):
                        received = True
                        yield chunk
                except ProviderError:
                    raise
                except Exception as direct_exc:
                    raise ProviderError(
                        _gemini_error_message(direct_exc, direct_retry_failed=True)
                    ) from direct_exc
            else:
                raise ProviderError(_gemini_error_message(first_exc)) from first_exc
        if not received:
            raise ProviderError("Gemini returned an empty answer.")

    def generate(self, prompt: str) -> str:
        answer = "".join(self.generate_stream(prompt)).strip()
        if not answer:
            raise ProviderError("Gemini returned an empty answer.")
        return answer


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

    def __init__(
        self,
        question: str,
        context: list[RetrievedChunk],
        conversation_context: tuple[dict[str, Any], ...] | list[dict[str, Any]] = (),
    ) -> None:
        self.question = question
        self.context = context
        self.conversation_context = tuple(conversation_context)

    def generate(self, prompt: str) -> str:  # noqa: ARG002 - common provider API
        if not self.context:
            if self.conversation_context:
                previous_answer = str(
                    self.conversation_context[-1].get("answer") or ""
                ).strip()
                if previous_answer:
                    return (
                        "Follow-up outline — use the previous answer as context, then address "
                        "the new question directly:\n\n"
                        f"Previous answer context:\n{previous_answer}\n\n"
                        "Keep the response focused on the new question and add only a new "
                        "reason, clarification or example."
                    )
            lowered = self.question.lower()
            if any(
                marker in lowered
                for marker in ("career change", "current field", "offered this job", "position")
            ):
                return (
                    "I would make the decision based on the direction I have deliberately "
                    "committed to, the responsibilities of each role and where I can contribute "
                    "most strongly over the long term. I would compare both offers carefully, "
                    "honour any commitment I had already made and communicate transparently "
                    "with everyone involved. I would not treat another offer as an automatic "
                    "reason to leave; I would choose the position that best fits my considered "
                    "career direction and then commit fully to that decision."
                )
            return (
                "I would answer this directly and honestly, focusing on the experience most "
                "relevant to the question and the value I can bring. I would support that with "
                "one clear example, explain what I personally did and finish with the outcome "
                "or what I learned. I would keep the answer specific to facts I can verify and "
                "avoid overstating my experience."
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
        follow_up_note = ""
        if self.conversation_context:
            previous = self.conversation_context[-1]
            previous_question = str(
                previous.get("resolved_question") or previous.get("question") or ""
            ).strip()
            if previous_question:
                follow_up_note = (
                    "\n\nFollow-up focus: connect this answer to the previous question — "
                    f"{previous_question}"
                )
        return (
            "Local grounded outline — turn these verified points into your own spoken answer:\n\n"
            f"{bullets}{follow_up_note}\n\n"
            "Suggested structure: give a direct opening, explain your strongest relevant example, "
            "then finish with the result or what you learned."
        )
