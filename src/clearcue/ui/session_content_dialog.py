from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from clearcue.storage.database import Database


class SessionContentDialog(QDialog):
    def __init__(
        self,
        database: Database,
        session_id: int,
        mode: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.database = database
        self.session_id = session_id
        self.mode = mode
        title = "Meeting transcript" if mode == "transcript" else "Generated answers and notes"
        self.setWindowTitle(title)
        self.resize(700, 500)

        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("SectionTitle")
        layout.addWidget(heading)
        self.content = QPlainTextEdit()
        self.content.setReadOnly(True)
        self.content.setPlainText(self._render_content())
        layout.addWidget(self.content, 1)

        actions = QHBoxLayout()
        copy = QPushButton("Copy")
        copy.clicked.connect(
            lambda: QApplication.clipboard().setText(self.content.toPlainText())
        )
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        actions.addWidget(copy)
        actions.addStretch()
        actions.addWidget(close)
        layout.addLayout(actions)

    def _render_content(self) -> str:
        if self.mode == "transcript":
            lines = []
            for entry in self.database.session_transcript(self.session_id):
                stamp = str(entry["created_at"]).replace("T", " ")[11:19]
                marker = " [question]" if entry["is_question"] else ""
                lines.append(f"{stamp}  {entry['speaker']}{marker}\n{entry['text']}")
            return "\n\n".join(lines) or "This meeting has no saved transcript."

        notes = []
        for index, entry in enumerate(self.database.session_answers(self.session_id), start=1):
            sources = tuple(str(source) for source in entry.get("sources", ()))
            source_line = f"\nSources: {', '.join(sources)}" if sources else ""
            notes.append(
                f"Answer {index}\nQuestion: {entry['question']}\n\n{entry['answer']}{source_line}"
            )
        return "\n\n---\n\n".join(notes) or "No generated answers were saved for this meeting."
