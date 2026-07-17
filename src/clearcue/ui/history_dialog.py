from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from clearcue.storage.database import Database
from clearcue.ui.popup_helpers import (
    session_display_datetime,
    session_display_duration,
    session_display_model,
    session_display_title,
)


class HistoryDialog(QDialog):
    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.database = database
        self.current_session_id: int | None = None
        self.setWindowTitle("Session History")
        self.resize(800, 560)
        layout = QVBoxLayout(self)
        note = QLabel("Only locally saved transcripts appear here. Raw audio is never stored.")
        note.setObjectName("Muted")
        layout.addWidget(note)

        splitter = QSplitter()
        self.sessions = QListWidget()
        self.sessions.currentItemChanged.connect(self._show_session)
        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        splitter.addWidget(self.sessions)
        splitter.addWidget(self.transcript)
        splitter.setSizes([260, 540])
        layout.addWidget(splitter, 1)

        actions = QHBoxLayout()
        export = QPushButton("Export transcript")
        export.clicked.connect(self._export)
        delete = QPushButton("Delete session")
        delete.setObjectName("Danger")
        delete.clicked.connect(self._delete)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        actions.addWidget(export)
        actions.addWidget(delete)
        actions.addStretch()
        actions.addWidget(close)
        layout.addLayout(actions)
        self._load()

    def _load(self) -> None:
        self.sessions.clear()
        profiles = {profile.id: profile.name for profile in self.database.list_profiles()}
        for session in self.database.list_sessions():
            metadata = " · ".join(
                (
                    session_display_datetime(session.started_at),
                    session_display_duration(session.started_at, session.ended_at),
                    session_display_model(session.model_used),
                )
            )
            item = QListWidgetItem(
                f"{session_display_title(session)}\n{metadata}\n"
                f"{profiles.get(session.profile_id, 'Profile')}"
            )
            item.setData(256, session.id)
            self.sessions.addItem(item)
        if self.sessions.count():
            self.sessions.setCurrentRow(0)

    def _show_session(self, current: QListWidgetItem | None, previous=None) -> None:  # noqa: ARG002
        if current is None:
            self.current_session_id = None
            self.transcript.clear()
            return
        self.current_session_id = int(current.data(256))
        lines = []
        for entry in self.database.session_transcript(self.current_session_id):
            stamp = str(entry["created_at"]).replace("T", " ")[11:19]
            marker = " [question]" if entry["is_question"] else ""
            lines.append(f"{stamp}  {entry['speaker']}{marker}\n{entry['text']}")
        self.transcript.setPlainText("\n\n".join(lines) or "This session has no saved transcript.")

    def _export(self) -> None:
        if self.current_session_id is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export transcript",
            f"prxmpt-session-{self.current_session_id}.txt",
            "Text files (*.txt)",
        )
        if path:
            Path(path).write_text(self.transcript.toPlainText(), encoding="utf-8")

    def _delete(self) -> None:
        if self.current_session_id is None:
            return
        if QMessageBox.question(
            self, "Delete session", "Permanently delete this local session?"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.database.delete_session(self.current_session_id)
        self.current_session_id = None
        self._load()
