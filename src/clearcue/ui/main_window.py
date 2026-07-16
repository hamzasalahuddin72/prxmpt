from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from clearcue.config import AppConfig, ConfigStore
from clearcue.services.session_controller import SessionController
from clearcue.services.updater import ReleaseInfo, UpdateService
from clearcue.storage.database import Database
from clearcue.ui.context_dialog import ContextDialog
from clearcue.ui.history_dialog import HistoryDialog
from clearcue.ui.overlay import OverlayWindow
from clearcue.ui.settings_dialog import SettingsDialog


class HotkeyBridge(QObject):
    toggle_session = Signal()
    generate = Signal()
    toggle_overlay = Signal()


def _card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 10, 12, 12)
    layout.setSpacing(8)
    return frame, layout


class MainWindow(QMainWindow):
    def __init__(
        self,
        database: Database,
        config_store: ConfigStore,
        config: AppConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.database = database
        self.config_store = config_store
        self.config = config
        self.controller = SessionController(database, config_store, config, self)
        self.updater = UpdateService(self)
        self._available_release: ReleaseInfo | None = None
        self._manual_update_check = False
        self.overlay = OverlayWindow(config.overlay_opacity)
        self.overlay.resize(config.overlay_width, config.overlay_height)
        self.hotkey_bridge = HotkeyBridge(self)

        self.setWindowTitle("ClearCue 1.0.6 — Reliability Build")
        self.resize(1100, 720)
        self.setMinimumSize(840, 600)
        self._build_ui()
        self._connect_signals()
        self._load_profiles()
        self.statusBar().showMessage("Ready")
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(6 * 60 * 60 * 1000)
        self.update_timer.timeout.connect(self._automatic_update_check)
        self.update_timer.start()
        if self.config.auto_check_updates:
            QTimer.singleShot(4000, self._automatic_update_check)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 8)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("CLEARCUE 1.0.6")
        title.setObjectName("Title")
        header.addWidget(title)
        mode = QLabel("RELIABILITY MODE")
        mode.setObjectName("ModeBadge")
        header.addWidget(mode)
        header.addStretch()
        header.addWidget(QLabel("PROFILE"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(190)
        header.addWidget(self.profile_combo)
        context_button = QPushButton("Context")
        context_button.clicked.connect(self.open_context)
        history_button = QPushButton("History")
        history_button.clicked.connect(self.open_history)
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.open_settings)
        updates_button = QPushButton("Updates")
        updates_button.clicked.connect(self.check_updates)
        overlay_button = QPushButton("Overlay")
        overlay_button.clicked.connect(self.toggle_overlay)
        for button in (
            context_button,
            history_button,
            settings_button,
            updates_button,
            overlay_button,
        ):
            header.addWidget(button)
        root.addLayout(header)

        self.update_banner = QFrame()
        self.update_banner.setObjectName("UpdateBanner")
        update_layout = QHBoxLayout(self.update_banner)
        update_layout.setContentsMargins(8, 6, 8, 6)
        self.update_label = QLabel("")
        self.update_label.setObjectName("UpdateText")
        self.update_label.setWordWrap(True)
        update_layout.addWidget(self.update_label, 1)
        self.update_progress = QProgressBar()
        self.update_progress.setRange(0, 100)
        self.update_progress.setTextVisible(True)
        self.update_progress.setFixedWidth(150)
        self.update_progress.hide()
        update_layout.addWidget(self.update_progress)
        self.update_notes_button = QPushButton("Release notes")
        self.update_notes_button.clicked.connect(self._open_release_notes)
        update_layout.addWidget(self.update_notes_button)
        self.update_install_button = QPushButton("Download and install")
        self.update_install_button.setObjectName("Primary")
        self.update_install_button.clicked.connect(self._download_update)
        update_layout.addWidget(self.update_install_button)
        update_later_button = QPushButton("Later")
        update_later_button.clicked.connect(self.update_banner.hide)
        update_layout.addWidget(update_later_button)
        self.update_banner.hide()
        root.addWidget(self.update_banner)

        session_card, session_layout = _card()
        section = QLabel("LIVE SESSION")
        section.setObjectName("SectionTitle")
        session_header = QHBoxLayout()
        session_header.addWidget(section)
        self.session_status = QLabel("STOPPED")
        self.session_status.setObjectName("StatusText")
        session_header.addWidget(self.session_status)
        session_header.addStretch()
        session_layout.addLayout(session_header)
        self.consent = QCheckBox(
            "I confirm that transcription is permitted and participants are informed where required."
        )
        self.consent.setChecked(self.config.consent_acknowledged)
        session_layout.addWidget(self.consent)
        session_controls = QHBoxLayout()
        self.session_button = QPushButton("Start listening")
        self.session_button.setObjectName("Primary")
        self.session_button.clicked.connect(self.toggle_session)
        session_controls.addWidget(self.session_button)
        shortcut_note = QLabel("Ctrl+Alt+S session  |  Ctrl+Alt+A answer  |  Ctrl+Alt+O overlay")
        shortcut_note.setObjectName("Muted")
        session_controls.addWidget(shortcut_note)
        session_controls.addStretch()
        session_layout.addLayout(session_controls)

        audio_row = QHBoxLayout()
        audio_row.addWidget(QLabel("MEETING"))
        self.interviewer_device_status = QLabel("OFF")
        self.interviewer_device_status.setObjectName("SourceOff")
        self.interviewer_device_status.setMinimumWidth(92)
        audio_row.addWidget(self.interviewer_device_status)
        self.interviewer_level = QProgressBar()
        self.interviewer_level.setRange(0, 100)
        self.interviewer_level.setTextVisible(False)
        audio_row.addWidget(self.interviewer_level, 1)
        audio_row.addSpacing(12)
        audio_row.addWidget(QLabel("MIC"))
        self.microphone_device_status = QLabel("OFF")
        self.microphone_device_status.setObjectName("SourceOff")
        self.microphone_device_status.setMinimumWidth(92)
        audio_row.addWidget(self.microphone_device_status)
        self.user_level = QProgressBar()
        self.user_level.setRange(0, 100)
        self.user_level.setTextVisible(False)
        audio_row.addWidget(self.user_level, 1)
        session_layout.addLayout(audio_row)

        self.error_banner = QLabel("")
        self.error_banner.setObjectName("ErrorBanner")
        self.error_banner.setWordWrap(True)
        self.error_banner.hide()
        session_layout.addWidget(self.error_banner)
        root.addWidget(session_card)

        context_row = QHBoxLayout()
        context_label = QLabel("GROUNDING")
        context_label.setObjectName("SectionTitle")
        context_row.addWidget(context_label)
        self.context_summary = QLabel()
        self.context_summary.setWordWrap(True)
        self.context_summary.setObjectName("Muted")
        context_row.addWidget(self.context_summary, 1)
        root.addLayout(context_row)

        transcript_card, transcript_layout = _card()
        transcript_title = QLabel("LIVE TRANSCRIPT")
        transcript_title.setObjectName("SectionTitle")
        transcript_layout.addWidget(transcript_title)
        self.transcript_view = QPlainTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setMaximumBlockCount(1000)
        self.transcript_view.setPlaceholderText(
            "Meeting audio and microphone transcription will appear here."
        )
        transcript_layout.addWidget(self.transcript_view, 1)

        answer_card, answer_layout = _card()
        answer_title = QLabel("QUESTION AND ANSWER")
        answer_title.setObjectName("SectionTitle")
        answer_layout.addWidget(answer_title)
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Type a practice question or wait for detection…")
        self.question_input.returnPressed.connect(self.generate_answer)
        answer_layout.addWidget(self.question_input)
        options = QHBoxLayout()
        self.style_combo = QComboBox()
        self.style_combo.addItem("Concise", "concise")
        self.style_combo.addItem("Detailed", "detailed")
        self.style_combo.addItem("STAR", "star")
        self.style_combo.addItem("Technical", "technical")
        style_index = self.style_combo.findData(self.config.answer_style)
        self.style_combo.setCurrentIndex(max(0, style_index))
        self.ask_button = QPushButton("Generate answer")
        self.ask_button.setObjectName("Primary")
        self.ask_button.clicked.connect(self.generate_answer)
        options.addWidget(self.style_combo)
        options.addWidget(self.ask_button)
        answer_layout.addLayout(options)
        self.answer_view = QPlainTextEdit()
        self.answer_view.setReadOnly(True)
        self.answer_view.setPlaceholderText("The suggestion will use only your imported context.")
        answer_layout.addWidget(self.answer_view, 1)
        self.sources_label = QLabel("")
        self.sources_label.setObjectName("Muted")
        self.sources_label.setWordWrap(True)
        answer_layout.addWidget(self.sources_label)

        workspace = QSplitter(Qt.Orientation.Horizontal)
        workspace.setChildrenCollapsible(False)
        workspace.addWidget(transcript_card)
        workspace.addWidget(answer_card)
        workspace.setSizes([560, 540])
        root.addWidget(workspace, 1)

    def _connect_signals(self) -> None:
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        self.controller.transcript_ready.connect(self._show_transcript)
        self.controller.question_ready.connect(self._show_question)
        self.controller.answer_ready.connect(self._show_answer)
        self.controller.status_changed.connect(self._show_status)
        self.controller.level_changed.connect(self._show_level)
        self.controller.source_state_changed.connect(self._show_source_state)
        self.controller.error_raised.connect(self._show_error)
        self.controller.session_state_changed.connect(self._session_state)
        self.updater.update_available.connect(self._show_update_available)
        self.updater.no_update.connect(self._show_no_update)
        self.updater.check_failed.connect(self._show_update_check_failed)
        self.updater.download_progress.connect(self._show_update_progress)
        self.updater.download_failed.connect(self._show_update_download_failed)
        self.updater.installer_ready.connect(self._install_downloaded_update)
        self.overlay.regenerate_requested.connect(self.generate_answer)
        self.overlay.main_window_requested.connect(self._bring_to_front)
        self.hotkey_bridge.toggle_session.connect(self.toggle_session)
        self.hotkey_bridge.generate.connect(self.generate_answer)
        self.hotkey_bridge.toggle_overlay.connect(self.toggle_overlay)

    def _load_profiles(self, selected_id: int | None = None) -> None:
        selected_id = selected_id or self.controller.profile_id
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in self.database.list_profiles():
            self.profile_combo.addItem(profile.name, profile.id)
        index = self.profile_combo.findData(selected_id)
        self.profile_combo.setCurrentIndex(max(0, index))
        self.profile_combo.blockSignals(False)
        self._profile_changed()

    def _profile_changed(self) -> None:
        value = self.profile_combo.currentData()
        if value is None:
            return
        profile_id = int(value)
        self.controller.set_profile(profile_id)
        documents = self.database.list_documents(profile_id)
        if documents:
            names = ", ".join(document.title for document in documents[:3])
            more = f" and {len(documents) - 3} more" if len(documents) > 3 else ""
            self.context_summary.setText(f"{len(documents)} context item(s): {names}{more}")
        else:
            self.context_summary.setText("No context has been added to this profile yet.")

    def open_context(self) -> None:
        dialog = ContextDialog(self.database, self.controller.profile_id, self)
        dialog.exec()
        self._load_profiles(dialog.selected_profile_id)

    def open_history(self) -> None:
        HistoryDialog(self.database, self).exec()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.config = dialog.result_config
            self.controller.update_config(self.config)
            self.overlay.setWindowOpacity(1.0)
            index = self.style_combo.findData(self.config.answer_style)
            if index >= 0:
                self.style_combo.setCurrentIndex(index)
            self.statusBar().showMessage("Settings saved", 4000)

    def check_updates(self) -> None:
        self._manual_update_check = True
        self.statusBar().showMessage("Checking for ClearCue updates…")
        self.updater.check_for_updates()

    def _automatic_update_check(self) -> None:
        if self.config.auto_check_updates:
            self.updater.check_for_updates()

    def _show_update_available(self, release: ReleaseInfo) -> None:
        self._available_release = release
        self._manual_update_check = False
        self.update_label.setText(
            f"ClearCue {release.version} is available. The verified update can be installed here."
        )
        self.update_progress.hide()
        self.update_install_button.setEnabled(True)
        self.update_install_button.setText("Download and install")
        self.update_banner.show()
        self.statusBar().showMessage(f"ClearCue {release.version} update available", 8000)

    def _show_no_update(self, current_version: str) -> None:
        if self._manual_update_check:
            self.statusBar().showMessage(
                f"ClearCue {current_version} is the latest published version.",
                6000,
            )
        self._manual_update_check = False

    def _show_update_check_failed(self, message: str) -> None:
        if self._manual_update_check:
            self.statusBar().showMessage(message, 8000)
        self._manual_update_check = False

    def _open_release_notes(self) -> None:
        if self._available_release and self._available_release.page_url:
            QDesktopServices.openUrl(QUrl(self._available_release.page_url))

    def _download_update(self) -> None:
        if not self._available_release:
            return
        self.update_install_button.setEnabled(False)
        self.update_install_button.setText("Downloading…")
        self.update_progress.setValue(0)
        self.update_progress.show()
        self.updater.download(self._available_release)

    def _show_update_progress(self, percent: int) -> None:
        self.update_progress.setValue(max(0, min(100, percent)))

    def _show_update_download_failed(self, message: str) -> None:
        self.update_install_button.setEnabled(True)
        self.update_install_button.setText("Try again")
        self._show_error(f"Update failed safely: {message}")

    def _install_downloaded_update(self, installer_path: str) -> None:
        self.update_install_button.setText("Starting installer…")
        self.statusBar().showMessage("Installing the verified ClearCue update…")
        if self.controller.running:
            self.controller.stop()
        if self.updater.launch_installer(installer_path):
            QTimer.singleShot(300, QApplication.instance().quit)

    def toggle_session(self) -> None:
        if self.controller.running:
            self.controller.stop()
            return
        self.config.consent_acknowledged = self.consent.isChecked()
        self.controller.update_config(self.config)
        self.error_banner.hide()
        self.controller.start()

    def generate_answer(self) -> None:
        self.controller.ask(
            self.question_input.text(),
            str(self.style_combo.currentData() or "concise"),
        )

    def toggle_overlay(self) -> None:
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            self.overlay.show()
            self.overlay.raise_()

    def _show_transcript(self, speaker: str, text: str, is_question: bool) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        marker = "  [question]" if is_question else ""
        self.transcript_view.appendPlainText(f"{timestamp}  {speaker}{marker}\n{text}\n")

    def _show_question(self, question: str) -> None:
        self.question_input.setText(question)
        self.overlay.set_question(question)

    def _show_answer(self, question: str, answer: str, sources: object) -> None:
        source_tuple = tuple(str(source) for source in (sources or ()))
        self.answer_view.setPlainText(answer)
        self.sources_label.setText(
            f"Grounded in: {', '.join(source_tuple)}"
            if source_tuple
            else "No matching context source"
        )
        self.overlay.set_answer(question, answer, source_tuple)

    def _show_status(self, message: str) -> None:
        self.session_status.setText(message)
        self.overlay.set_status(message)
        self.statusBar().showMessage(message)

    def _show_level(self, source: str, value: float) -> None:
        bar = self.interviewer_level if source == "Interviewer" else self.user_level
        bar.setValue(round(max(0.0, min(1.0, value)) * 100))

    def _show_error(self, message: str) -> None:
        self.statusBar().showMessage(message, 8000)
        self.error_banner.setText(message)
        self.error_banner.show()

    def _show_source_state(self, kind: str, available: bool, message: str) -> None:
        label = (
            self.microphone_device_status
            if kind == "microphone"
            else self.interviewer_device_status
        )
        if not self.controller.running:
            label.setText("OFF")
            label.setToolTip("")
            label.setObjectName("SourceOff")
            label.style().unpolish(label)
            label.style().polish(label)
            return
        label.setText("CONNECTED" if available else "RETRYING")
        label.setToolTip(message)
        label.setObjectName("SourceOn" if available else "SourceRetry")
        label.style().unpolish(label)
        label.style().polish(label)

    def _session_state(self, running: bool) -> None:
        self.session_button.setText("Stop listening" if running else "Start listening")
        self.session_button.setObjectName("Danger" if running else "Primary")
        self.session_button.style().unpolish(self.session_button)
        self.session_button.style().polish(self.session_button)
        self.profile_combo.setEnabled(not running)
        if not running:
            self.session_status.setText("STOPPED")
            for label in (self.interviewer_device_status, self.microphone_device_status):
                label.setText("OFF")
                label.setToolTip("")
                label.setObjectName("SourceOff")
                label.style().unpolish(label)
                label.style().polish(label)

    def _bring_to_front(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.updater.shutdown()
        self.overlay.close()
        self.controller.shutdown()
        super().closeEvent(event)
