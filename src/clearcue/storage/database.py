from __future__ import annotations

import sqlite3
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

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


@dataclass(frozen=True, slots=True)
class SessionTurn:
    """The durable state for one detected question and its answer attempt.

    This is intentionally separate from the existing transcript and answer
    history tables.  Older installations can keep using those tables while
    newer pipeline stages adopt an ordered turn contract incrementally.
    """

    id: int
    session_id: int
    turn_index: int
    created_at: str
    question: str
    resolved_question: str
    answer: str
    follow_up_of_turn_id: int | None
    follow_up_reason: str
    relevance_status: str
    relevance_reason: str
    context: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    novelty_status: str = "unchecked"
    novelty_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class InterviewerProfile:
    """Confidence-scored interviewer signals persisted for one session."""

    session_id: int
    tone: str
    tone_confidence: float
    pace: str
    pace_confidence: float
    emotion: str
    emotion_confidence: float
    style: dict[str, Any]
    sample_count: int
    updated_at: str


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
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    turn_id INTEGER,
                    relevance_status TEXT NOT NULL DEFAULT 'unknown',
                    relevance_reason TEXT NOT NULL DEFAULT '',
                    novelty_status TEXT NOT NULL DEFAULT 'unchecked',
                    novelty_metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS session_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    turn_index INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    question TEXT NOT NULL,
                    resolved_question TEXT NOT NULL DEFAULT '',
                    answer TEXT NOT NULL DEFAULT '',
                    follow_up_of_turn_id INTEGER,
                    follow_up_reason TEXT NOT NULL DEFAULT '',
                    relevance_status TEXT NOT NULL DEFAULT 'unknown',
                    relevance_reason TEXT NOT NULL DEFAULT '',
                    context_json TEXT NOT NULL DEFAULT '[]',
                    novelty_status TEXT NOT NULL DEFAULT 'unchecked',
                    novelty_metadata_json TEXT NOT NULL DEFAULT '{}',
                    UNIQUE(session_id, turn_index)
                );

                CREATE INDEX IF NOT EXISTS idx_session_turns_session_order
                    ON session_turns(session_id, turn_index);

                CREATE TABLE IF NOT EXISTS session_context (
                    session_id INTEGER PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
                    context_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS session_interviewer_profiles (
                    session_id INTEGER PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
                    tone TEXT NOT NULL DEFAULT '',
                    tone_confidence REAL NOT NULL DEFAULT 0,
                    pace TEXT NOT NULL DEFAULT '',
                    pace_confidence REAL NOT NULL DEFAULT 0,
                    emotion TEXT NOT NULL DEFAULT '',
                    emotion_confidence REAL NOT NULL DEFAULT 0,
                    style_json TEXT NOT NULL DEFAULT '{}',
                    sample_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(
                connection,
                "sessions",
                "model_used",
                "TEXT NOT NULL DEFAULT ''",
            )
            for column, definition in (
                ("turn_id", "INTEGER"),
                ("relevance_status", "TEXT NOT NULL DEFAULT 'unknown'"),
                ("relevance_reason", "TEXT NOT NULL DEFAULT ''"),
                ("novelty_status", "TEXT NOT NULL DEFAULT 'unchecked'"),
                ("novelty_metadata_json", "TEXT NOT NULL DEFAULT '{}'"),
            ):
                self._ensure_column(connection, "session_answers", column, definition)
            self._ensure_column(
                connection,
                "session_turns",
                "follow_up_reason",
                "TEXT NOT NULL DEFAULT ''",
            )
        self.ensure_default_profile()

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        columns = {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )

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
        *,
        turn_id: int | None = None,
        relevance_status: str = "unknown",
        relevance_reason: str = "",
        novelty_status: str = "unchecked",
        novelty_metadata: Mapping[str, Any] | None = None,
    ) -> None:
        metadata_json = json.dumps(dict(novelty_metadata or {}), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO session_answers(
                    session_id, created_at, question, answer, sources_json,
                    turn_id, relevance_status, relevance_reason,
                    novelty_status, novelty_metadata_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    _now(),
                    question.strip(),
                    answer.strip(),
                    json.dumps(tuple(sources)),
                    turn_id,
                    relevance_status.strip() or "unknown",
                    relevance_reason.strip(),
                    novelty_status.strip() or "unchecked",
                    metadata_json,
                ),
            )
            if turn_id is not None:
                connection.execute(
                    """
                    UPDATE session_turns
                    SET answer = ?, novelty_status = ?, novelty_metadata_json = ?
                    WHERE id = ? AND session_id = ?
                    """,
                    (
                        answer.strip(),
                        novelty_status.strip() or "unchecked",
                        metadata_json,
                        turn_id,
                        session_id,
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
                SELECT created_at, question, answer, sources_json, turn_id,
                       relevance_status, relevance_reason, novelty_status,
                       novelty_metadata_json
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
            try:
                decoded_metadata = json.loads(str(item.pop("novelty_metadata_json")))
                item["novelty_metadata"] = (
                    decoded_metadata if isinstance(decoded_metadata, dict) else {}
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                item["novelty_metadata"] = {}
                item.pop("novelty_metadata_json", None)
            answers.append(item)
        return answers

    def create_session_turn(
        self,
        session_id: int,
        question: str,
        *,
        resolved_question: str = "",
        follow_up_of_turn_id: int | None = None,
        follow_up_reason: str = "",
        relevance_status: str = "unknown",
        relevance_reason: str = "",
        context: Iterable[Mapping[str, Any]] = (),
    ) -> int:
        """Create the next ordered turn without changing legacy answer flow."""

        cleaned_question = " ".join(question.split())
        if not cleaned_question:
            raise ValueError("Turn question cannot be empty.")
        context_json = json.dumps(
            [dict(item) for item in context],
            sort_keys=True,
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if follow_up_of_turn_id is not None:
                parent = connection.execute(
                    "SELECT session_id FROM session_turns WHERE id = ?",
                    (follow_up_of_turn_id,),
                ).fetchone()
                if parent is None or int(parent["session_id"]) != session_id:
                    raise ValueError("Follow-up turn must belong to the same session.")
            row = connection.execute(
                "SELECT COALESCE(MAX(turn_index), 0) + 1 AS next_index "
                "FROM session_turns WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            cursor = connection.execute(
                """
                INSERT INTO session_turns(
                    session_id, turn_index, created_at, question, resolved_question,
                    follow_up_of_turn_id, follow_up_reason, relevance_status,
                    relevance_reason, context_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    int(row["next_index"]),
                    _now(),
                    cleaned_question,
                    " ".join(resolved_question.split()),
                    follow_up_of_turn_id,
                    follow_up_reason.strip(),
                    relevance_status.strip() or "unknown",
                    relevance_reason.strip(),
                    context_json,
                ),
            )
            return int(cursor.lastrowid)

    def update_session_turn(
        self,
        turn_id: int,
        *,
        resolved_question: str | None = None,
        answer: str | None = None,
        relevance_status: str | None = None,
        relevance_reason: str | None = None,
        context: Iterable[Mapping[str, Any]] | None = None,
        novelty_status: str | None = None,
        novelty_metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Update only supplied turn fields, preserving compatibility with old callers."""

        updates: dict[str, Any] = {}
        if resolved_question is not None:
            updates["resolved_question"] = " ".join(resolved_question.split())
        if answer is not None:
            updates["answer"] = answer.strip()
        if relevance_status is not None:
            updates["relevance_status"] = relevance_status.strip() or "unknown"
        if relevance_reason is not None:
            updates["relevance_reason"] = relevance_reason.strip()
        if context is not None:
            updates["context_json"] = json.dumps(
                [dict(item) for item in context], sort_keys=True
            )
        if novelty_status is not None:
            updates["novelty_status"] = novelty_status.strip() or "unchecked"
        if novelty_metadata is not None:
            updates["novelty_metadata_json"] = json.dumps(
                dict(novelty_metadata), sort_keys=True
            )
        if not updates:
            return
        assignments = ", ".join(f"{column} = ?" for column in updates)
        values = [*updates.values(), turn_id]
        with self._connect() as connection:
            connection.execute(
                f"UPDATE session_turns SET {assignments} WHERE id = ?",
                values,
            )

    def session_turns(
        self,
        session_id: int,
        limit: int | None = None,
    ) -> list[SessionTurn]:
        query = """
            SELECT id, session_id, turn_index, created_at, question, resolved_question,
                   answer, follow_up_of_turn_id, relevance_status, relevance_reason,
                   follow_up_reason, context_json, novelty_status, novelty_metadata_json
            FROM session_turns WHERE session_id = ? ORDER BY turn_index
        """
        parameters: list[Any] = [session_id]
        if limit is not None:
            if limit < 1:
                return []
            query += " LIMIT ?"
            parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        turns: list[SessionTurn] = []
        for row in rows:
            context = self._decode_json_list(row["context_json"])
            metadata = self._decode_json_object(row["novelty_metadata_json"])
            turns.append(
                SessionTurn(
                    id=int(row["id"]),
                    session_id=int(row["session_id"]),
                    turn_index=int(row["turn_index"]),
                    created_at=str(row["created_at"]),
                    question=str(row["question"]),
                    resolved_question=str(row["resolved_question"]),
                    answer=str(row["answer"]),
                    follow_up_of_turn_id=(
                        int(row["follow_up_of_turn_id"])
                        if row["follow_up_of_turn_id"] is not None
                        else None
                    ),
                    follow_up_reason=str(row["follow_up_reason"]),
                    relevance_status=str(row["relevance_status"]),
                    relevance_reason=str(row["relevance_reason"]),
                    context=tuple(context),
                    novelty_status=str(row["novelty_status"]),
                    novelty_metadata=metadata,
                )
            )
        return turns

    def save_session_context(
        self,
        session_id: int,
        context: Iterable[Mapping[str, Any]],
    ) -> None:
        context_json = json.dumps([dict(item) for item in context], sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO session_context(session_id, context_json, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    context_json = excluded.context_json,
                    updated_at = excluded.updated_at
                """,
                (session_id, context_json, _now()),
            )

    def session_context(self, session_id: int) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT context_json FROM session_context WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return ()
        return tuple(self._decode_json_list(row["context_json"]))

    def update_interviewer_profile(
        self,
        session_id: int,
        *,
        tone: str | None = None,
        tone_confidence: float | None = None,
        pace: str | None = None,
        pace_confidence: float | None = None,
        emotion: str | None = None,
        emotion_confidence: float | None = None,
        style: Mapping[str, Any] | None = None,
        sample_count: int | None = None,
    ) -> InterviewerProfile:
        """Merge confidence-scored interviewer signals for the active session."""

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM session_interviewer_profiles WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            current = dict(existing) if existing else {}
            values = {
                "tone": tone if tone is not None else current.get("tone", ""),
                "tone_confidence": self._confidence(
                    tone_confidence
                    if tone_confidence is not None
                    else current.get("tone_confidence", 0)
                ),
                "pace": pace if pace is not None else current.get("pace", ""),
                "pace_confidence": self._confidence(
                    pace_confidence
                    if pace_confidence is not None
                    else current.get("pace_confidence", 0)
                ),
                "emotion": emotion if emotion is not None else current.get("emotion", ""),
                "emotion_confidence": self._confidence(
                    emotion_confidence
                    if emotion_confidence is not None
                    else current.get("emotion_confidence", 0)
                ),
                "style_json": json.dumps(
                    dict(style)
                    if style is not None
                    else self._decode_json_object(current.get("style_json", "{}")),
                    sort_keys=True,
                ),
                "sample_count": max(
                    0,
                    int(sample_count)
                    if sample_count is not None
                    else int(current.get("sample_count", 0)),
                ),
                "updated_at": _now(),
            }
            connection.execute(
                """
                INSERT INTO session_interviewer_profiles(
                    session_id, tone, tone_confidence, pace, pace_confidence,
                    emotion, emotion_confidence, style_json, sample_count, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    tone = excluded.tone,
                    tone_confidence = excluded.tone_confidence,
                    pace = excluded.pace,
                    pace_confidence = excluded.pace_confidence,
                    emotion = excluded.emotion,
                    emotion_confidence = excluded.emotion_confidence,
                    style_json = excluded.style_json,
                    sample_count = excluded.sample_count,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    str(values["tone"]).strip(),
                    values["tone_confidence"],
                    str(values["pace"]).strip(),
                    values["pace_confidence"],
                    str(values["emotion"]).strip(),
                    values["emotion_confidence"],
                    values["style_json"],
                    values["sample_count"],
                    values["updated_at"],
                ),
            )
            row = connection.execute(
                "SELECT * FROM session_interviewer_profiles WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return self._interviewer_profile_from_row(row)

    def interviewer_profile(self, session_id: int) -> InterviewerProfile | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM session_interviewer_profiles WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return self._interviewer_profile_from_row(row) if row else None

    @staticmethod
    def _confidence(value: object) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _decode_json_list(value: object) -> list[dict[str, Any]]:
        try:
            decoded = json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(decoded, list):
            return []
        return [dict(item) for item in decoded if isinstance(item, Mapping)]

    @staticmethod
    def _decode_json_object(value: object) -> dict[str, Any]:
        try:
            decoded = json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return dict(decoded) if isinstance(decoded, Mapping) else {}

    @classmethod
    def _interviewer_profile_from_row(
        cls,
        row: sqlite3.Row | Mapping[str, Any] | None,
    ) -> InterviewerProfile | None:
        if row is None:
            return None
        return InterviewerProfile(
            session_id=int(row["session_id"]),
            tone=str(row["tone"]),
            tone_confidence=cls._confidence(row["tone_confidence"]),
            pace=str(row["pace"]),
            pace_confidence=cls._confidence(row["pace_confidence"]),
            emotion=str(row["emotion"]),
            emotion_confidence=cls._confidence(row["emotion_confidence"]),
            style=cls._decode_json_object(row["style_json"]),
            sample_count=int(row["sample_count"]),
            updated_at=str(row["updated_at"]),
        )

    def delete_session(self, session_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
