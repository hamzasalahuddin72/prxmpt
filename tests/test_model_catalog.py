import json

from clearcue.config import AppConfig
from clearcue.intelligence import model_catalog as catalog_module
from clearcue.intelligence.model_catalog import (
    AvailableModel,
    _answer_capable_openai_model,
    _ollama_models,
    discover_available_models,
)
from clearcue.intelligence.providers import GeminiProvider


class _Model:
    def __init__(self, name: str, label: str, actions: tuple[str, ...]) -> None:
        self.name = name
        self.display_name = label
        self.supported_actions = actions


class _Models:
    def list(self):
        return iter(
            (
                _Model(
                    "models/gemini-3.5-flash",
                    "Gemini 3.5 Flash",
                    ("generateContent",),
                ),
                _Model(
                    "models/gemini-embedding-2",
                    "Gemini Embedding 2",
                    ("embedContent",),
                ),
                _Model(
                    "models/gemini-3.1-flash-image",
                    "Gemini Image",
                    ("generateContent",),
                ),
            )
        )


class _Client:
    def __init__(self) -> None:
        self.models = _Models()
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_gemini_catalog_uses_only_text_generation_models(monkeypatch) -> None:
    client = _Client()
    monkeypatch.setattr(
        GeminiProvider,
        "_client",
        lambda self, *, trust_env=True, timeout_ms=45_000: client,
    )
    models = GeminiProvider("valid", "gemini-3.5-flash").list_available_models()
    assert models == [("gemini-3.5-flash", "Gemini 3.5 Flash")]
    assert client.closed


def test_openai_catalog_filter_excludes_non_answer_endpoints() -> None:
    assert _answer_capable_openai_model("gpt-5.6")
    assert _answer_capable_openai_model("o4-mini")
    assert not _answer_capable_openai_model("gpt-image-1")
    assert not _answer_capable_openai_model("gpt-5.6-codex")
    assert not _answer_capable_openai_model("text-embedding-3-small")


def test_ollama_catalog_lists_only_installed_models(monkeypatch) -> None:
    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {"models": [{"model": "qwen3:8b"}, {"name": "gemma3:4b"}]}
            ).encode()

    monkeypatch.setattr(
        catalog_module.urllib.request,
        "urlopen",
        lambda request, timeout: _Response(),
    )
    assert _ollama_models("http://127.0.0.1:11434") == [
        AvailableModel("ollama", "gemma3:4b", "gemma3:4b"),
        AvailableModel("ollama", "qwen3:8b", "qwen3:8b"),
    ]


def test_discovery_hides_cloud_provider_without_a_valid_key(monkeypatch) -> None:
    monkeypatch.setattr(catalog_module, "get_gemini_key", lambda: "invalid")
    monkeypatch.setattr(catalog_module, "get_openai_key", lambda: "")
    monkeypatch.setattr(
        GeminiProvider,
        "list_available_models",
        lambda self: (_ for _ in ()).throw(RuntimeError("rejected")),
    )
    monkeypatch.setattr(catalog_module, "_ollama_models", lambda _url: [])
    catalog = discover_available_models(AppConfig(answer_provider="gemini"))
    assert catalog.models == (
        AvailableModel("local", "local", "Grounded outline"),
    )
    assert catalog.unavailable_providers == ("gemini",)


def test_discovery_returns_valid_gemini_models_without_generation(monkeypatch) -> None:
    monkeypatch.setattr(catalog_module, "get_gemini_key", lambda: "valid")
    monkeypatch.setattr(catalog_module, "get_openai_key", lambda: "")
    monkeypatch.setattr(
        GeminiProvider,
        "list_available_models",
        lambda self: [("gemini-3.5-flash", "Gemini 3.5 Flash")],
    )
    monkeypatch.setattr(catalog_module, "_ollama_models", lambda _url: [])
    catalog = discover_available_models(AppConfig(answer_provider="gemini"))
    assert AvailableModel(
        "gemini",
        "gemini-3.5-flash",
        "Gemini 3.5 Flash",
    ) in catalog.models
