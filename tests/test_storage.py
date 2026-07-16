from pathlib import Path

from clearcue.storage.database import Database


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

    session_id = database.create_session(profile_id)
    database.add_transcript(session_id, "Interviewer", "Why this role?", True)
    database.finish_session(session_id)
    transcript = database.session_transcript(session_id)
    assert transcript[0]["speaker"] == "Interviewer"
    assert transcript[0]["is_question"] == 1

    database.delete_session(session_id)
    assert database.session_transcript(session_id) == []
    database.delete_document(document_id)
    assert database.context_chunks(profile_id) == []

