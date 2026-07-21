from __future__ import annotations

import sqlite3
from pathlib import Path

from clearcue.storage.database import Database


def test_legacy_answer_rows_gain_intelligence_metadata_without_data_loss(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE profiles (
                id INTEGER PRIMARY KEY,
                name TEXT,
                created_at TEXT
            );
            INSERT INTO profiles VALUES (1, 'Legacy', '2026-07-17T00:00:00+00:00');
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY,
                profile_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                title TEXT NOT NULL
            );
            INSERT INTO sessions VALUES
                (7, 1, '2026-07-17T10:00:00+00:00', NULL, 'Legacy meeting');
            CREATE TABLE session_answers (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]'
            );
            INSERT INTO session_answers VALUES
                (3, 7, '2026-07-17T10:01:00+00:00', 'Why?', 'Because.', '["CV"]');
            """
        )

    database = Database(path)

    answer = database.session_answers(7)[0]
    assert answer["question"] == "Why?"
    assert answer["answer"] == "Because."
    assert answer["sources"] == ("CV",)
    assert answer["relevance_status"] == "unknown"
    assert answer["novelty_status"] == "unchecked"
    assert answer["novelty_metadata"] == {}


def test_ordered_turn_context_and_profile_state_are_session_scoped(tmp_path: Path) -> None:
    database = Database(tmp_path / "intelligence.db")
    profile_id = database.ensure_default_profile()
    session_id = database.create_session(profile_id)

    first_turn = database.create_session_turn(
        session_id,
        "Tell me about your experience.",
        relevance_status="accepted",
        context=({"role": "interviewer", "text": "Tell me about your experience."},),
    )
    second_turn = database.create_session_turn(
        session_id,
        "Why?",
        resolved_question="Why did you choose that approach?",
        follow_up_of_turn_id=first_turn,
        relevance_status="accepted",
    )
    database.update_session_turn(
        first_turn,
        answer="I chose it because it reduced operational risk.",
        novelty_status="approved",
        novelty_metadata={"new_points": 1, "repeated_points": []},
    )

    turns = database.session_turns(session_id)
    assert [turn.turn_index for turn in turns] == [1, 2]
    assert turns[1].follow_up_of_turn_id == first_turn
    assert turns[1].resolved_question == "Why did you choose that approach?"
    assert turns[0].answer.startswith("I chose it")
    assert turns[0].novelty_metadata["new_points"] == 1

    database.save_session_context(
        session_id,
        (
            {"turn_index": 1, "question": "Tell me about your experience."},
            {"turn_index": 2, "question": "Why did you choose that approach?"},
        ),
    )
    assert database.session_context(session_id)[1]["turn_index"] == 2

    profile = database.update_interviewer_profile(
        session_id,
        tone="formal",
        tone_confidence=1.4,
        pace="fast-paced",
        pace_confidence=0.8,
        emotion="neutral",
        emotion_confidence=0.65,
        style={"question_type": "open-ended"},
        sample_count=4,
    )
    assert profile.tone == "formal"
    assert profile.tone_confidence == 1.0
    assert profile.style["question_type"] == "open-ended"
    assert database.interviewer_profile(session_id) == profile

    database.delete_session(session_id)
    assert database.session_turns(session_id) == []
    assert database.session_context(session_id) == ()
    assert database.interviewer_profile(session_id) is None


def test_follow_up_turn_must_belong_to_the_same_session(tmp_path: Path) -> None:
    database = Database(tmp_path / "intelligence.db")
    profile_id = database.ensure_default_profile()
    first_session = database.create_session(profile_id)
    second_session = database.create_session(profile_id)
    first_turn = database.create_session_turn(first_session, "What is your approach?")

    try:
        database.create_session_turn(
            second_session,
            "Why?",
            follow_up_of_turn_id=first_turn,
        )
    except ValueError as exc:
        assert "same session" in str(exc)
    else:
        raise AssertionError("A follow-up from another session should be rejected")
