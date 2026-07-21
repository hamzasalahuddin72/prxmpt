from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication

from clearcue.config import AppConfig, ConfigStore
from clearcue.intelligence.prompt_builder import build_prompt
from clearcue.intelligence.turn_context import TurnContextWindow
from clearcue.services.session_controller import SessionController
from clearcue.storage.database import Database


def test_short_referential_question_resolves_against_previous_turn() -> None:
    window = TurnContextWindow()
    first = window.resolve("Tell me about your Python experience")
    assert not first.is_follow_up
    window.add_turn(first.question, resolved_question=first.resolved_question)
    window.complete_turn(first.question, "I built an invoice intelligence application.")

    follow_up = window.resolve("Why did you choose it?")
    assert follow_up.is_follow_up
    assert follow_up.parent_turn_index == 1
    assert follow_up.context[0]["answer"].startswith("I built an invoice")


def test_standalone_question_does_not_inherit_context_without_reference() -> None:
    window = TurnContextWindow()
    window.add_turn("Tell me about your Python experience")
    assert not window.resolve("What is your preferred programming language?").is_follow_up


def test_continuation_detail_question_locks_to_the_previous_topic() -> None:
    window = TurnContextWindow()
    window.add_turn(
        "Tell me about a time that you worked on a team",
        answer=(
            "I built a sneaker market website in a six-person Agile team using PHP, "
            "JavaScript, RapidAPI and Git."
        ),
    )

    follow_up = window.resolve("What was your role and what was the outcome?")

    assert follow_up.status == "accepted_follow_up"
    assert follow_up.is_follow_up
    assert follow_up.parent_turn_index == 1
    assert follow_up.topic_lock_turn_index == 1
    assert len(follow_up.context) == 1
    assert "sneaker market" in follow_up.context[0]["answer"]


def test_database_detail_question_stays_with_an_active_technical_topic() -> None:
    window = TurnContextWindow()
    window.add_turn(
        "Talk me through a team website project",
        answer=(
            "Our six-person team built a sneaker market website with PHP, JavaScript, "
            "RapidAPI and Git."
        ),
    )

    follow_up = window.resolve("Can you tell me a bit more about what kind of database?")

    assert follow_up.status == "accepted_follow_up"
    assert follow_up.topic_lock_turn_index == 1
    assert follow_up.follow_up_score >= 0.38


def test_contextual_asr_repair_requires_a_supported_active_topic() -> None:
    window = TurnContextWindow()
    window.add_turn(
        "Talk me through a team website project",
        answer=(
            "Our six-person team built a sneaker market website with PHP, JavaScript, "
            "RapidAPI and Git."
        ),
    )

    repaired = window.resolve("What was the text tag?")

    assert repaired.status == "repaired_follow_up"
    assert repaired.resolved_question == "What was the tech stack?"
    assert repaired.topic_lock_turn_index == 1
    assert repaired.repair_confidence >= 0.92


def test_fragmented_question_needs_clarification_without_a_provider_answer() -> None:
    window = TurnContextWindow()
    window.add_turn("Talk me through a team website project")

    decision = window.resolve("Did you create for the application for the website?")

    assert decision.status == "clarification_needed"
    assert not decision.is_answerable
    assert "repeat or rephrase" in decision.clarification_message


def test_context_window_is_bounded_and_resettable() -> None:
    window = TurnContextWindow(max_turns=2, max_chars=260)
    for index in range(4):
        question = f"Tell me about project {index}"
        window.add_turn(question)
        window.complete_turn(question, "A verified answer with enough detail to exercise compaction.")

    payload = window.context_payload()
    assert len(payload) <= 2
    assert payload[-1]["question"] == "Tell me about project 3"
    assert sum(len(str(item)) for item in payload) <= 420

    window.reset()
    assert window.turns == ()
    assert window.context_payload() == ()
    assert not window.resolve("Why?").is_follow_up


def test_prompt_includes_only_the_compact_session_window() -> None:
    prompt = build_prompt(
        "Why did you choose it?",
        [],
        conversation_context=(
            {
                "turn_index": 1,
                "question": "Tell me about your Python experience",
                "resolved_question": "Tell me about your Python experience",
                "answer": "I built an invoice intelligence application.",
            },
        ),
    )
    assert "ROLLING SESSION CONTEXT" in prompt
    assert "I built an invoice intelligence application." in prompt
    assert "Why did you choose it?" in prompt


def test_controller_persists_follow_up_link_and_context(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    database = Database(tmp_path / "controller.db")
    profile_id = database.ensure_default_profile()
    session_id = database.create_session(profile_id)
    controller = SessionController(
        database,
        ConfigStore(tmp_path / "settings.json"),
        AppConfig(auto_generate=False, save_transcripts=True),
    )
    controller.session_id = session_id

    controller._question_parts[:] = ["Tell me about your Python experience"]
    controller._commit_pending_question(auto_generate=False)
    first_turn_id = database.session_turns(session_id)[0].id

    controller._handle_answer(
        0,
        "Tell me about your Python experience?",
        "I built an invoice intelligence application.",
        (),
        "local",
    )

    controller._question_parts[:] = ["Why did you choose it?"]
    controller._commit_pending_question(auto_generate=False)
    turns = database.session_turns(session_id)
    assert len(turns) == 2
    assert turns[1].follow_up_of_turn_id == first_turn_id
    assert turns[1].follow_up_reason
    assert database.session_context(session_id)[0]["answer"].startswith("I built")
    assert turns[1].relevance_status == "accepted_follow_up"
    assert turns[1].gate_metadata["decision_version"] == 1
    controller.shutdown()
    app.processEvents()
