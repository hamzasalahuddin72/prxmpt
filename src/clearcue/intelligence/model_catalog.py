from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from clearcue.config import AppConfig
from clearcue.intelligence.providers import GeminiProvider
from clearcue.security import SecretStoreError, get_gemini_key, get_openai_key


@dataclass(frozen=True, slots=True)
class AvailableModel:
    provider: str
    model_id: str
    label: str

    @property
    def key(self) -> tuple[str, str]:
        return self.provider, self.model_id


@dataclass(frozen=True, slots=True)
class ModelCatalog:
    models: tuple[AvailableModel, ...]
    unavailable_providers: tuple[str, ...] = ()


def _answer_capable_openai_model(model_id: str) -> bool:
    lowered = model_id.lower()
    if not re.match(r"^(gpt-|o\d)", lowered):
        return False
    excluded = (
        "audio",
        "codex",
        "embedding",
        "image",
        "moderation",
        "realtime",
        "search",
        "transcribe",
        "tts",
    )
    return not any(marker in lowered for marker in excluded)


def _openai_models(api_key: str) -> list[AvailableModel]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key.strip(), timeout=10.0, max_retries=0)
    try:
        identifiers = {
            str(item.id).strip()
            for item in client.models.list().data
            if _answer_capable_openai_model(str(item.id).strip())
        }
    finally:
        client.close()
    return [
        AvailableModel("openai", model_id, model_id)
        for model_id in sorted(identifiers, key=str.casefold)
    ]


def _ollama_models(base_url: str) -> list[AvailableModel]:
    endpoint = base_url.rstrip("/") + "/api/tags"
    request = urllib.request.Request(endpoint, method="GET")
    with urllib.request.urlopen(request, timeout=3) as response:
        payload = json.loads(response.read().decode("utf-8"))
    identifiers = {
        str(item.get("model") or item.get("name") or "").strip()
        for item in payload.get("models", ())
        if isinstance(item, dict)
    }
    return [
        AvailableModel("ollama", model_id, model_id)
        for model_id in sorted(filter(None, identifiers), key=str.casefold)
    ]


def discover_available_models(config: AppConfig) -> ModelCatalog:
    """Return only models whose credential/service can currently list them.

    Model-list requests contain no transcript, question or résumé content and do
    not perform a paid generation. Local and installed Ollama models require no
    cloud credential and remain valid offline choices.
    """

    models = [AvailableModel("local", "local", "Grounded outline")]
    unavailable: list[str] = []

    try:
        gemini_key = get_gemini_key().strip()
    except SecretStoreError:
        gemini_key = ""
        unavailable.append("gemini")
    if gemini_key:
        try:
            models.extend(
                AvailableModel("gemini", model_id, label)
                for model_id, label in GeminiProvider(
                    gemini_key,
                    config.gemini_model,
                ).list_available_models()
            )
        except Exception:
            unavailable.append("gemini")

    try:
        openai_key = get_openai_key().strip()
    except SecretStoreError:
        openai_key = ""
        unavailable.append("openai")
    if openai_key:
        try:
            models.extend(_openai_models(openai_key))
        except Exception:
            unavailable.append("openai")

    try:
        models.extend(_ollama_models(config.ollama_url))
    except (OSError, urllib.error.URLError, ValueError, TypeError):
        # Ollama is optional. A stopped local service should not be presented as
        # an error or leave a non-working model in the dropdown.
        pass

    unique = {model.key: model for model in models}
    ordered = sorted(
        unique.values(),
        key=lambda item: (
            {"gemini": 0, "openai": 1, "ollama": 2, "local": 3}.get(
                item.provider,
                9,
            ),
            item.label.casefold(),
        ),
    )
    return ModelCatalog(tuple(ordered), tuple(dict.fromkeys(unavailable)))
