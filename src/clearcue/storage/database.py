from __future__ import annotations

import sqlite3
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from clearcue.paths import database_path


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Profile:
    id: int
    name: str
    created_at: str


@dataclass(frozen=True, slots=True)
class Document:
    id: int
    profile_id: int
    title: str
    source_type: str
    created_at: str


@dataclass(frozen=True, slots=True)
class SessionSummary:
    id: int
    profile_id: int
    started_at: str
    ended_at: str | None
    title: str
    model_used: str = ""


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    original_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS context_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_profile
                    ON context_chunks(profile_id);

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL REFERENCES profiles(id),
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    title TEXT NOT NULL,
                    model_used TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS transcript_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    text TEXT NOT NULL,
                    is_question INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS session_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    sources_json TEXT NOT NULL DEFAULT '[]'
                );
                """
            )
            session_columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(sessions)").fetchall()
            }
            if "model_used" not in session_columns:
                connection.execute(
                    "ALTER TABLE sessions ADD COLUMN model_used TEXT NOT NULL DEFAULT ''"
                )
        self.ensure_default_profile()

    def ensure_default_profile(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT id FROM profiles ORDER BY id LIMIT 1").fetchone()
            if row:
                return int(row["id"])
            cursor = connection.execute(
                "INSERT INTO profiles(name, created_at) VALUES(?, ?)",
                ("My interview profile", _now()),
            )
            return int(cursor.lastrowid)

    def create_profile(self, name: str) -> int:
        cleaned = " ".join(name.split())
        if not cleaned:
            raise ValueError("Profile name cannot be empty.")
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO profiles(name, created_at) VALUES(?, ?)",
                (cleaned, _now()),
            )
            return int(cursor.lastrowid)

    def list_profiles(self) -> list[Profile]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, name, created_at FROM profiles ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [Profile(int(row["id"]), row["name"], row["created_at"]) for row in rows]

    def rename_profile(self, profile_id: int, name: str) -> None:
        cleaned = " ".join(name.split())
        if not cleaned:
            raise ValueError("Profile name cannot be empty.")
        with self._connect() as connection:
            connection.execute("UPDATE profiles SET name = ? WHERE id = ?", (cleaned, profile_id))

    def add_document(
        self,
        profile_id: int,
        title: str,
        source_type: str,
        original_text: str,
        chunks: Iterable[str],
    ) -> int:
        cleaned = original_text.strip()
        if not cleaned:
            raise ValueError("The document does not contain readable text.")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO documents(profile_id, title, source_type, original_text, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (profile_id, title.strip() or "Untitled", source_type, cleaned, _now()),
            )
            document_id = int(cursor.lastrowid)
            connection.executemany(
                """
                INSERT INTO context_chunks(document_id, profile_id, chunk_index, content)
                VALUES(?, ?, ?, ?)
                """,
                [
                    (document_id, profile_id, index, chunk.strip())
                    for index, chunk in enumerate(chunks)
                    if chunk.strip()
                ],
            )
            return document_id

    def list_documents(self, profile_id: int) -> list[Document]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, profile_id, title, source_type, created_at
                FROM documents WHERE profile_id = ? ORDER BY created_at DESC, id DESC
                """,
                (profile_id,),
            ).fetchall()
        return [
            Document(
                int(row["id"]),
                int(row["profile_id"]),
                row["title"],
                row["source_type"],
                row["created_at"],
            )
            for row in rows
        ]

    def delete_document(self, document_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def context_chunks(self, profile_id: int) -> list[tuple[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT d.title, c.content
                FROM context_chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.profile_id = ?
                ORDER BY d.id, c.chunk_index
                """,
                (profile_id,),
            ).fetchall()
        return [(row["title"], row["content"]) for row in rows]

    def create_session(
        self,
        profile_id: int,
        title: str = "Practice session",
        model_used: str = "",
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO sessions(profile_id, started_at, title, model_used)
                VALUES(?, ?, ?, ?)
                """,
                (profile_id, _now(), title, model_used.strip()),
            )
            return int(cursor.lastrowid)

    def finish_session(self, session_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ?",
                (_now(), session_id),
            )

    def add_transcript(
        self,
        session_id: int,
        speaker: str,
        text: str,
        is_question: bool = False,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO transcript_entries(session_id, created_at, speaker, text, is_question)
                VALUES(?, ?, ?, ?, ?)
                """,
                (session_id, _now(), speaker, text.strip(), int(is_question)),
            )

    def list_sessions(self, limit: int = 50) -> list[SessionSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, profile_id, started_at, ended_at, title, model_used
                FROM sessions ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            SessionSummary(
                int(row["id"]),
                int(row["profile_id"]),
                row["started_at"],
                row["ended_at"],
                row["title"],
                row["model_used"],
            )
            for row in rows
        ]

    def session_transcript(self, session_id: int) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT created_at, speaker, text, is_question
                FROM transcript_entries WHERE session_id = ? ORDER BY id
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_session_answer(
        self,
        session_id: int,
        question: str,
        answer: str,
        sources: Iterable[str] = (),
        model_used: str = "",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO session_answers(session_id, created_at, question, answer, sources_json)
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    _now(),
                    question.strip(),
                    answer.strip(),
                    json.dumps(tuple(sources)),
                ),
            )
            if model_used.strip():
                connection.execute(
                    "UPDATE sessions SET model_used = ? WHERE id = ?",
                    (model_used.strip(), session_id),
                )

    def session_answers(self, session_id: int) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT created_at, question, answer, sources_json
                FROM session_answers WHERE session_id = ? ORDER BY id
                """,
                (session_id,),
            ).fetchall()
        answers = []
        for row in rows:
            item = dict(row)
            try:
                item["sources"] = tuple(json.loads(str(item.pop("sources_json"))))
            except (TypeError, ValueError, json.JSONDecodeError):
                item["sources"] = ()
                item.pop("sources_json", None)
            answers.append(item)
        return answers

    def delete_session(self, session_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
