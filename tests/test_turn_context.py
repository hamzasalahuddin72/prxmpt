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
    controller.shutdown()
    app.processEvents()

