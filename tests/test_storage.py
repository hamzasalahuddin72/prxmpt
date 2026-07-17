from pathlib import Path
import sqlite3

from clearcue.storage.database import Database


def test_existing_session_table_gains_model_metadata_without_data_loss(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE profiles (id INTEGER PRIMARY KEY, name TEXT, created_at TEXT)"
        )
        connection.execute(
            "INSERT INTO profiles VALUES (1, 'Legacy', '2026-07-17T00:00:00+00:00')"
        )
        connection.execute(
            """
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY,
                profile_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                title TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO sessions VALUES (7, 1, '2026-07-17T10:00:00+00:00', NULL, 'Legacy meeting')"
        )

    database = Database(path)
    session = database.list_sessions()[0]
    assert session.id == 7
    assert session.title == "Legacy meeting"
    assert session.model_used == ""


def test_profile_document_and_session_lifecycle(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.db")
    profile_id = database.create_profile("Data role")
    document_id = database.add_document(
        profile_id,
        "CV",
        "note",
        "Python and SQL project experience.",
        ["Python and SQL project experience."],
    )
    assert database.list_documents(profile_id)[0].id == document_id
    assert database.context_chunks(profile_id) == [
        ("CV", "Python and SQL project experience.")
    ]

    session_id = database.create_session(profile_id, model_used="gemini-3.5-flash")
    database.add_transcript(session_id, "Interviewer", "Why this role?", True)
    database.finish_session(session_id)
    transcript = database.session_transcript(session_id)
    assert transcript[0]["speaker"] == "Interviewer"
    assert transcript[0]["is_question"] == 1
    database.add_session_answer(
        session_id,
        "Why this role?",
        "The role matches my Python experience.",
        ("CV", "Job description"),
        "gpt-5.6",
    )
    answers = database.session_answers(session_id)
    assert answers[0]["question"] == "Why this role?"
    assert answers[0]["sources"] == ("CV", "Job description")
    assert database.list_sessions()[0].model_used == "gpt-5.6"

    database.delete_session(session_id)
    assert database.session_transcript(session_id) == []
    assert database.session_answers(session_id) == []
    database.delete_document(document_id)
    assert database.context_chunks(profile_id) == []
