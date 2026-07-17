from clearcue.config import AppConfig
from clearcue.intelligence.answer_service import AnswerService
from clearcue.intelligence import providers as provider_module
from clearcue.intelligence.providers import GeminiProvider, ProviderError
from clearcue.intelligence.prompt_builder import build_prompt
from clearcue.intelligence.question_detector import (
    detect_question,
    potential_question_candidate,
    question_fragment,
)
from clearcue.intelligence.retriever import ContextRetriever


CONTEXT = [
    (
        "CV",
        "Built an invoice intelligence application in Python using SQLite and Streamlit. "
        "It extracts invoice fields, validates missing values and detects duplicates.",
    ),
    (
        "Job description",
        "The role requires Python, data validation, communication and practical AI development.",
    ),
]

NOISY_CAREER_CHANGE_QUESTION = (
    "I think he's that one so they're rolling. I have to ask this question. "
    "Given that you are making a career change here, especially with finishing "
    "a master's degree in education, if If a position becomes available in your "
    "current field, down here in the Jackson-boat area. How do you approach being "
    "offered this job versus being offered a position in your field and... position "
    "becomes available in your current field down here in the Jacksonville area. "
    "How do you approach being offered this job versus being offered a position in "
    "your field? And I'm asking that in the now. in the future. Thank you. Shh."
)


def test_detects_direct_and_implicit_questions() -> None:
    assert detect_question("Can you describe a Python project you built")
    assert detect_question("Tell me about your experience with data validation.")
    assert detect_question("The weather is good today.") is None


def test_potential_question_candidate_isolates_trailing_sentence() -> None:
    text = "We are a technology company. Tell me about yourself"
    assert potential_question_candidate(text) == "Tell me about yourself"
    assert detect_question(text) == "Tell me about yourself?"


def test_statement_does_not_become_bold_from_ambiguous_prefix() -> None:
    assert potential_question_candidate("We are hiring engineers") is None
    assert potential_question_candidate("Why do you") == "Why do you"


def test_question_like_remark_reverts_when_sentence_finishes() -> None:
    assert potential_question_candidate("What a great result") == "What a great result"
    assert detect_question("What a great result.") is None


def test_noisy_repeated_transcript_reconstructs_the_complete_question() -> None:
    fragment = question_fragment(NOISY_CAREER_CHANGE_QUESTION)
    question = detect_question(NOISY_CAREER_CHANGE_QUESTION)
    assert fragment == (
        "How do you approach being offered this job versus being offered a position "
        "in your field?"
    )
    assert question is not None
    assert "career change" in question.lower()
    assert "master's degree in education" in question.lower()
    assert "jacksonville" in question.lower()
    assert "both now and in the future" in question.lower()
    assert question.lower().count("how do you approach") == 1


def test_retrieval_ranks_relevant_context() -> None:
    results = ContextRetriever(CONTEXT).retrieve("Describe your invoice Python project")
    assert results
    assert results[0].title == "CV"


def test_generic_motivation_question_still_retrieves_profile_context() -> None:
    results = ContextRetriever(CONTEXT).retrieve(
        "Why are you interested in this opportunity?"
    )
    assert results
    assert {result.title for result in results} == {"CV", "Job description"}


def test_prompt_contains_grounding_and_question() -> None:
    results = ContextRetriever(CONTEXT).retrieve("invoice project")
    prompt = build_prompt("What did you build?", results, "concise")
    assert "What did you build?" in prompt
    assert "Built an invoice intelligence" in prompt
    assert "Return only the spoken answer" in prompt
    assert "Do not mention the context, missing information, placeholders" in prompt


def test_local_answer_uses_context_without_api() -> None:
    service = AnswerService(AppConfig(answer_provider="local"), CONTEXT)
    result = service.generate("Can you describe your Python invoice project?")
    assert "invoice" in result.answer.lower()
    assert "CV" in result.sources


def test_local_answer_remains_useful_when_context_is_empty() -> None:
    result = AnswerService(AppConfig(answer_provider="local"), []).generate(
        "Tell me about your experience"
    )
    assert "i would answer this directly" in result.answer.lower()
    assert "more personal context" not in result.answer.lower()


def test_local_career_change_answer_commits_to_a_decision_framework() -> None:
    result = AnswerService(AppConfig(answer_provider="local"), []).generate(
        "How would you choose this job versus a position in your current field?"
    )
    assert "i would make the decision" in result.answer.lower()
    assert "commit" in result.answer.lower()


class _FakeModels:
    def __init__(self, events=None, error: Exception | None = None) -> None:
        self.events = events or []
        self.error = error
        self.request = None

    def generate_content_stream(self, **kwargs):
        self.request = kwargs
        if self.error:
            raise self.error
        return iter(self.events)


class _FakeGeminiClient:
    def __init__(self, models: _FakeModels) -> None:
        self.models = models
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_gemini_streams_stateless_text_deltas(monkeypatch) -> None:
    models = _FakeModels(
        [
            {"text": "First "},
            {"text": ""},
            {"text": "answer."},
        ]
    )
    client = _FakeGeminiClient(models)
    monkeypatch.setattr(
        GeminiProvider,
        "_client",
        lambda self, *, trust_env=True: client,
    )
    provider = GeminiProvider("secret", "gemini-3.5-flash")
    assert provider.generate("Tell me about yourself") == "First answer."
    assert models.request["model"] == "gemini-3.5-flash"
    assert "Tell me about yourself" in models.request["contents"]
    assert "interview practice" in models.request["config"]["system_instruction"]
    assert models.request["config"]["max_output_tokens"] == 800
    assert client.closed


def test_gemini_turns_quota_errors_into_actionable_message(monkeypatch) -> None:
    models = _FakeModels(error=RuntimeError("429 RESOURCE_EXHAUSTED"))
    client = _FakeGeminiClient(models)
    monkeypatch.setattr(
        GeminiProvider,
        "_client",
        lambda self, *, trust_env=True: client,
    )
    provider = GeminiProvider("secret", "gemini-3.1-flash-lite")
    try:
        provider.generate("question")
    except ProviderError as exc:
        assert "limit was reached" in str(exc)
    else:
        raise AssertionError("quota failure should raise ProviderError")


def test_gemini_bypasses_a_broken_configured_proxy_once(monkeypatch) -> None:
    primary = _FakeGeminiClient(_FakeModels(error=RuntimeError("Connection error")))
    direct = _FakeGeminiClient(_FakeModels(events=[{"text": "connected"}]))
    attempts: list[bool] = []

    def client_for_attempt(self, *, trust_env=True):
        attempts.append(trust_env)
        return primary if trust_env else direct

    monkeypatch.setattr(GeminiProvider, "_client", client_for_attempt)
    monkeypatch.setattr(provider_module, "_proxy_is_configured", lambda: True)

    assert GeminiProvider("secret", "gemini-3.5-flash").generate("test") == "connected"
    assert attempts == [True, False]
    assert primary.closed
    assert direct.closed


def test_gemini_connection_error_names_google_endpoint(monkeypatch) -> None:
    client = _FakeGeminiClient(_FakeModels(error=RuntimeError("Connection error")))
    monkeypatch.setattr(
        GeminiProvider,
        "_client",
        lambda self, *, trust_env=True: client,
    )
    monkeypatch.setattr(provider_module, "_proxy_is_configured", lambda: False)

    try:
        GeminiProvider("secret", "gemini-3.5-flash").generate("test")
    except ProviderError as exc:
        assert "generativelanguage.googleapis.com" in str(exc)
        assert "port 443" in str(exc)
    else:
        raise AssertionError("connection failure should raise ProviderError")


def test_answer_service_forwards_deltas_for_non_streaming_local_provider() -> None:
    deltas = []
    result = AnswerService(AppConfig(answer_provider="local"), CONTEXT).generate_stream(
        "Can you describe your Python invoice project?",
        on_delta=deltas.append,
    )
    assert deltas == [result.answer]
