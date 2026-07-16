from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from clearcue.documents.ingest import SUPPORTED_EXTENSIONS, chunk_text, extract_text
from clearcue.storage.database import Database


class ContextDialog(QDialog):
    def __init__(
        self,
        database: Database,
        selected_profile_id: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.database = database
        self.selected_profile_id = selected_profile_id
        self.setWindowTitle("Profiles and Context")
        self.resize(670, 520)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Add only information you can defend: your CV, job description, project notes "
            "and STAR examples. ClearCue uses these files to ground its suggestions."
        )
        intro.setWordWrap(True)
        intro.setObjectName("Muted")
        layout.addWidget(intro)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        profile_row.addWidget(self.profile_combo, 1)
        new_profile = QPushButton("New profile")
        new_profile.clicked.connect(self._new_profile)
        profile_row.addWidget(new_profile)
        layout.addLayout(profile_row)

        self.document_list = QListWidget()
        layout.addWidget(self.document_list, 1)

        actions = QHBoxLayout()
        import_button = QPushButton("Import PDF, DOCX or text")
        import_button.setObjectName("Primary")
        import_button.clicked.connect(self._import_files)
        note_button = QPushButton("Add pasted note")
        note_button.clicked.connect(self._add_note)
        delete_button = QPushButton("Delete selected")
        delete_button.setObjectName("Danger")
        delete_button.clicked.connect(self._delete_selected)
        actions.addWidget(import_button)
        actions.addWidget(note_button)
        actions.addStretch()
        actions.addWidget(delete_button)
        layout.addLayout(actions)

        close = QPushButton("Done")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self._load_profiles()

    def _load_profiles(self) -> None:
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in self.database.list_profiles():
            self.profile_combo.addItem(profile.name, profile.id)
        index = self.profile_combo.findData(self.selected_profile_id)
        self.profile_combo.setCurrentIndex(max(0, index))
        self.profile_combo.blockSignals(False)
        self._profile_changed()

    def _profile_changed(self) -> None:
        value = self.profile_combo.currentData()
        if value is None:
            return
        self.selected_profile_id = int(value)
        self.document_list.clear()
        for document in self.database.list_documents(self.selected_profile_id):
            item = QListWidgetItem(f"{document.title}  ·  {document.source_type.upper()}")
            item.setData(256, document.id)
            self.document_list.addItem(item)

    def _new_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New profile", "Profile name")
        if not ok or not name.strip():
            return
        try:
            self.selected_profile_id = self.database.create_profile(name)
            self._load_profiles()
        except Exception as exc:
            QMessageBox.warning(self, "Profile", str(exc))

    def _import_files(self) -> None:
        patterns = " ".join(f"*{extension}" for extension in sorted(SUPPORTED_EXTENSIONS))
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import context",
            "",
            f"Supported documents ({patterns});;All files (*)",
        )
        errors: list[str] = []
        for raw_path in paths:
            path = Path(raw_path)
            try:
                text = extract_text(path)
                self.database.add_document(
                    self.selected_profile_id,
                    path.name,
                    path.suffix.lower().lstrip("."),
                    text,
                    chunk_text(text),
                )
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        self._profile_changed()
        if errors:
            QMessageBox.warning(self, "Some files were not imported", "\n".join(errors))

    def _add_note(self) -> None:
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Add context note",
            "Paste a STAR story, job description or preparation note:",
        )
        if not ok or not text.strip():
            return
        title, title_ok = QInputDialog.getText(self, "Note title", "Title")
        if not title_ok:
            return
        self.database.add_document(
            self.selected_profile_id,
            title.strip() or "Pasted note",
            "note",
            text,
            chunk_text(text),
        )
        self._profile_changed()

    def _delete_selected(self) -> None:
        item = self.document_list.currentItem()
        if item is None:
            return
        if QMessageBox.question(
            self,
            "Delete context",
            "Delete the selected context document?",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.database.delete_document(int(item.data(256)))
        self._profile_changed()

