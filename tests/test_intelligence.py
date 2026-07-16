from clearcue.config import AppConfig
from clearcue.intelligence.answer_service import AnswerService
from clearcue.intelligence.prompt_builder import build_prompt
from clearcue.intelligence.question_detector import detect_question
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


def test_detects_direct_and_implicit_questions() -> None:
    assert detect_question("Can you describe a Python project you built")
    assert detect_question("Tell me about your experience with data validation.")
    assert detect_question("The weather is good today.") is None


def test_retrieval_ranks_relevant_context() -> None:
    results = ContextRetriever(CONTEXT).retrieve("Describe your invoice Python project")
    assert results
    assert results[0].title == "CV"


def test_prompt_contains_grounding_and_question() -> None:
    results = ContextRetriever(CONTEXT).retrieve("invoice project")
    prompt = build_prompt("What did you build?", results, "concise")
    assert "What did you build?" in prompt
    assert "Built an invoice intelligence" in prompt
    assert "Return only the suggested answer" in prompt


def test_local_answer_uses_context_without_api() -> None:
    service = AnswerService(AppConfig(answer_provider="local"), CONTEXT)
    result = service.generate("Can you describe your Python invoice project?")
    assert "invoice" in result.answer.lower()
    assert "CV" in result.sources


def test_local_answer_requests_context_when_empty() -> None:
    result = AnswerService(AppConfig(answer_provider="local"), []).generate(
        "Tell me about your experience"
    )
    assert "more personal context" in result.answer.lower()

