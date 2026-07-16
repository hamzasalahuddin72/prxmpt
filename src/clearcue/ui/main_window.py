from __future__ import annotations

from functools import partial

from PySide6.QtCore import QDir, QFile, QEvent, QObject, QPoint, QSize, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QCloseEvent,
    QDesktopServices,
    QIcon,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGraphicsOpacityEffect,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtUiTools import QUiLoader

from clearcue.config import AppConfig, ConfigStore
from clearcue.resources import resource_path
from clearcue.services.session_controller import SessionController
from clearcue.services.updater import ReleaseInfo, UpdateService
from clearcue.storage.database import Database
from clearcue.ui.context_dialog import ContextDialog
from clearcue.ui.history_dialog import HistoryDialog
from clearcue.ui.popup_helpers import (
    popup_size_for_screen,
    session_display_time,
    session_display_title,
)
from clearcue.ui.session_content_dialog import SessionContentDialog
from clearcue.ui.settings_dialog import SettingsDialog


DESIGN_WIDTH = 551
DESIGN_HEIGHT = 827
COLLAPSED_HEIGHT = 80


class HotkeyBridge(QObject):
    toggle_session = Signal()
    generate = Signal()
    toggle_overlay = Signal()


class ToggleSwitch(QCheckBox):
    """Toggle using the exact approved on-state asset."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(45, 45)
        self._on_pixmap = QPixmap(str(resource_path("toggle-on.png")))

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isChecked() and not self._on_pixmap.isNull():
            painter.drawPixmap(self.rect(), self._on_pixmap)
            return
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#55575c"))
        painter.drawRoundedRect(0, 13, 45, 19, 10, 10)
        painter.setBrush(QColor("#d8d9dc"))
        painter.drawEllipse(1, 11, 23, 23)


class PrxmptUiLoader(QUiLoader):
    """Load the Designer form while preserving the custom toggle widget."""

    def createWidget(
        self,
        class_name: str,
        parent: QWidget | None = None,
        name: str = "",
    ) -> QWidget:
        if class_name == "ToggleSwitch":
            widget = ToggleSwitch(parent)
            widget.setObjectName(name)
            return widget
        return super().createWidget(class_name, parent, name)


def _set_dynamic_property(widget: QWidget, name: str, value: object) -> None:
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


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
        self.hotkey_bridge = HotkeyBridge(self)
        self._available_release: ReleaseInfo | None = None
        self._manual_update_check = False
        self._drag_origin: QPoint | None = None
        self._drag_locked = bool(config.popup_drag_locked)
        self._collapsed = False
        self._expanded_size = (DESIGN_WIDTH, DESIGN_HEIGHT)
        self._ui_scale = 1.0
        self._initial_geometry_applied = False
        self._allow_quit = False
        self._cleaned_up = False
        self._tray_notice_shown = False

        self.setWindowTitle("prxmpt 1.0.9")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        target_width, target_height = self._target_popup_size()
        self._ui_scale = target_width / DESIGN_WIDTH
        self._expanded_size = (target_width, target_height)
        self.setFixedSize(target_width, target_height)
        self.setWindowIcon(self._make_app_icon())

        self._build_ui()
        self._connect_signals()
        self._setup_tray()
        self._refresh_model_badge()
        self._refresh_audio_buttons()
        self._refresh_history()
        self._update_drag_button()

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(6 * 60 * 60 * 1000)
        self.update_timer.timeout.connect(self._automatic_update_check)
        self.update_timer.start()
        if self.config.auto_check_updates:
            QTimer.singleShot(4000, self._automatic_update_check)

    @staticmethod
    def _make_app_icon() -> QIcon:
        return QIcon(str(resource_path("prxmpt.ico")))

    def _target_popup_size(self) -> tuple[int, int]:
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return DESIGN_WIDTH, DESIGN_HEIGHT
        available = screen.availableGeometry()
        return popup_size_for_screen(
            available.width(),
            available.height(),
            DESIGN_WIDTH,
            DESIGN_HEIGHT,
        )

    @staticmethod
    def _icon_button(
        text: str = "",
        object_name: str = "HeaderIcon",
        asset: str | None = None,
        icon_size: tuple[int, int] | None = None,
    ) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if asset:
            button.setText("")
            button.setIcon(QIcon(str(resource_path(asset))))
            if icon_size:
                button.setIconSize(QSize(*icon_size))
        return button

    @staticmethod
    def _required_child(form: QWidget, widget_type: type, object_name: str):
        widget = form.findChild(widget_type, object_name)
        if widget is None:
            raise RuntimeError(
                f"The editable prxmpt-main.ui form is missing {object_name}."
            )
        return widget

    @staticmethod
    def _configure_asset_button(
        button: QPushButton,
        asset: str,
        icon_size: tuple[int, int],
    ) -> None:
        button.setText("")
        button.setIcon(QIcon(str(resource_path(asset))))
        button.setIconSize(QSize(*icon_size))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _build_ui(self) -> None:
        ui_path = resource_path("prxmpt-main.ui")
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QFile.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Unable to open the editable UI form: {ui_path}")
        loader = PrxmptUiLoader()
        loader.setWorkingDirectory(QDir(str(ui_path.parent)))
        try:
            form = loader.load(ui_file)
        finally:
            ui_file.close()
        if not isinstance(form, QWidget):
            raise RuntimeError(
                f"Unable to load the editable UI form: {loader.errorString()}"
            )
        self._designer_form = form

        if self._ui_scale < 0.999:
            scene = QGraphicsScene(self)
            scene.setSceneRect(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT)
            scene.addWidget(form)
            view = QGraphicsView(scene)
            view.setObjectName("TransparentPanel")
            view.setStyleSheet("background: transparent; border: 0;")
            view.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            view.setFrameShape(QFrame.Shape.NoFrame)
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            view.setRenderHints(
                QPainter.RenderHint.Antialiasing
                | QPainter.RenderHint.TextAntialiasing
                | QPainter.RenderHint.SmoothPixmapTransform
            )
            view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
            view.scale(self._ui_scale, self._ui_scale)
            self._graphics_view: QGraphicsView | None = view
            self._graphics_scene: QGraphicsScene | None = scene
            self.setCentralWidget(view)
        else:
            self._graphics_view = None
            self._graphics_scene = None
            self.setCentralWidget(form)

        find = self._required_child
        self.popup_frame = find(form, QFrame, "PopupRoot")
        self.header = find(form, QFrame, "PopupHeader")
        self.body = find(form, QWidget, "TransparentPanel")
        self.settings_button = find(form, QPushButton, "SettingsIcon")
        self.brand = find(form, QLabel, "PopupBrand")
        self.drag_button = find(form, QPushButton, "DragIcon")
        self.collapse_button = find(form, QPushButton, "PrivacyIcon")
        self.close_button = find(form, QPushButton, "PopupClose")
        self.microphone_button = find(form, QPushButton, "MicrophoneButton")
        self.speaker_button = find(form, QPushButton, "SpeakerButton")
        self.live_button = find(form, QPushButton, "LiveButton")
        self.question_input = find(form, QPlainTextEdit, "QuestionInput")
        self.ask_button = find(form, QPushButton, "AnswerButton")
        self.transcription_indicator = find(form, QLabel, "TranscriptionIndicator")
        self.clear_button = find(form, QPushButton, "ClearButton")
        self.error_banner = find(form, QLabel, "PopupError")
        self.answer_view = find(form, QPlainTextEdit, "AnswerView")
        self.model_badge = find(form, QPushButton, "ModelBadge")
        self.auto_answer_switch = find(form, ToggleSwitch, "AutoAnswerSwitch")
        self.stealth_switch = find(form, ToggleSwitch, "StealthSwitch")
        auto_label = find(form, QLabel, "AutoAnswerLabel")
        stealth_label = find(form, QLabel, "StealthLabel")
        self.history_card = find(form, QFrame, "HistoryCard")
        history_layout = self.history_card.layout()
        if not isinstance(history_layout, QVBoxLayout):
            raise RuntimeError("The editable UI form is missing HistoryLayout.")
        self.history_layout = history_layout

        self.microphone_button.setObjectName("AudioSourceButton")
        self.speaker_button.setObjectName("AudioSourceButton")
        auto_label.setObjectName("ToggleLabel")
        stealth_label.setObjectName("ToggleLabel")

        for button, asset, size in (
            (self.settings_button, "settings.png", (35, 35)),
            (self.drag_button, "drag-lock.png", (26, 26)),
            (self.collapse_button, "collapse.png", (31, 31)),
            (self.close_button, "exit.png", (26, 26)),
            (self.microphone_button, "microphone.png", (53, 53)),
            (self.speaker_button, "speaker.png", (68, 68)),
        ):
            self._configure_asset_button(button, asset, size)
        self.brand.setPixmap(QPixmap(str(resource_path("prxmpt-logo.png"))))
        self.brand.setScaledContents(True)
        self.brand.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        indicator = QPixmap(str(resource_path("transcribing.png")))
        self.transcription_indicator.setPixmap(
            indicator.scaled(
                59,
                59,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.transcription_indicator.hide()
        self.error_banner.hide()
        self.question_input.setMaximumBlockCount(8)
        self.session_button = self.live_button

        self.header.installEventFilter(self)
        self.settings_button.setToolTip("Settings, profile, context and updates")
        self.settings_button.clicked.connect(self._show_control_menu)
        self.drag_button.clicked.connect(self._toggle_drag_lock)
        self.collapse_button.setToolTip("Collapse prxmpt to the title bar")
        self.collapse_button.clicked.connect(self._toggle_collapsed)
        self.close_button.setToolTip("Minimize prxmpt to the system tray")
        self.close_button.clicked.connect(self.minimize_to_tray)
        self.microphone_button.setToolTip("Enable or disable microphone capture")
        self.microphone_button.clicked.connect(
            partial(self._toggle_audio_source, "microphone")
        )
        self.speaker_button.setToolTip("Enable or disable meeting-audio capture")
        self.speaker_button.clicked.connect(
            partial(self._toggle_audio_source, "loopback")
        )
        self.live_button.setToolTip("Start listening")
        self.live_button.clicked.connect(self.toggle_session)
        self.ask_button.clicked.connect(self.generate_answer)
        self.clear_button.clicked.connect(self._clear_workspace)
        self.model_badge.setToolTip("Open answer and model settings")
        self.model_badge.clicked.connect(self.open_settings)
        self.auto_answer_switch.setChecked(self.config.auto_generate)
        self.auto_answer_switch.setToolTip(
            "Generate an answer when a question is detected"
        )
        self.auto_answer_switch.toggled.connect(self._set_auto_answer)
        self.stealth_switch.setToolTip("Reserved for a future prxmpt feature")

    def _connect_signals(self) -> None:
        self.controller.transcript_ready.connect(self._show_transcript)
        self.controller.question_ready.connect(self._show_question)
        self.controller.answer_ready.connect(self._show_answer)
        self.controller.status_changed.connect(self._show_status)
        self.controller.level_changed.connect(self._show_level)
        self.controller.source_state_changed.connect(self._show_source_state)
        self.controller.error_raised.connect(self._show_error)
        self.controller.session_state_changed.connect(self._session_state)
        self.controller.transcribing_changed.connect(self._show_transcribing)
        self.updater.update_available.connect(self._show_update_available)
        self.updater.no_update.connect(self._show_no_update)
        self.updater.check_failed.connect(self._show_update_check_failed)
        self.updater.download_progress.connect(self._show_update_progress)
        self.updater.download_failed.connect(self._show_update_download_failed)
        self.updater.installer_ready.connect(self._install_downloaded_update)
        self.hotkey_bridge.toggle_session.connect(self.toggle_session)
        self.hotkey_bridge.generate.connect(self.generate_answer)
        self.hotkey_bridge.toggle_overlay.connect(self.toggle_popup)

    def _setup_tray(self) -> None:
        self.tray: QSystemTrayIcon | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(self.windowIcon(), self)
        tray.setToolTip("prxmpt")
        menu = QMenu(self)
        show_action = QAction("Show prxmpt", menu)
        show_action.triggered.connect(self._bring_to_front)
        session_action = QAction("Start / stop listening", menu)
        session_action.triggered.connect(self.toggle_session)
        quit_action = QAction("Quit prxmpt", menu)
        quit_action.triggered.connect(self.quit_application)
        menu.addAction(show_action)
        menu.addAction(session_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        tray.setContextMenu(menu)
        self._tray_menu = menu
        tray.activated.connect(self._tray_activated)
        tray.show()
        self.tray = tray

    def _show_control_menu(self) -> None:
        menu = QMenu(self)
        profile_name = next(
            (
                profile.name
                for profile in self.database.list_profiles()
                if profile.id == self.controller.profile_id
            ),
            "Current profile",
        )
        profile_action = menu.addAction(f"Profile: {profile_name}")
        profile_action.setEnabled(False)
        menu.addSeparator()
        settings = menu.addAction("Settings")
        settings.triggered.connect(self.open_settings)
        context = menu.addAction("Profiles and context")
        context.triggered.connect(self.open_context)
        history = menu.addAction("Full meeting history")
        history.triggered.connect(self._open_full_history)
        menu.addSeparator()
        if self._available_release:
            update = menu.addAction(f"Install prxmpt {self._available_release.version}")
            update.triggered.connect(self._prompt_update_install)
            notes = menu.addAction("Open release notes")
            notes.triggered.connect(self._open_release_notes)
        else:
            update = menu.addAction("Check for updates")
            update.triggered.connect(self.check_updates)
        menu.addSeparator()
        quit_action = menu.addAction("Quit prxmpt")
        quit_action.triggered.connect(self.quit_application)
        menu.exec(self.settings_button.mapToGlobal(self.settings_button.rect().bottomLeft()))

    def open_context(self) -> None:
        dialog = ContextDialog(self.database, self.controller.profile_id, self)
        dialog.exec()
        self.controller.set_profile(dialog.selected_profile_id)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if not dialog.exec():
            return
        self.config = dialog.result_config
        self.controller.update_config(self.config)
        self.auto_answer_switch.setChecked(self.config.auto_generate)
        self._refresh_model_badge()
        self._refresh_audio_buttons()

    def _open_full_history(self) -> None:
        HistoryDialog(self.database, self).exec()
        self._refresh_history()

    def _refresh_model_badge(self) -> None:
        if self.config.answer_provider == "openai":
            model = self.config.openai_model.replace("gpt-", "gpt-")
            if model.startswith("gpt-5.6"):
                model = "gpt-5.6"
        elif self.config.answer_provider == "ollama":
            model = self.config.ollama_model
        else:
            model = "local"
        self.model_badge.setText(model[:10])

    def _refresh_audio_buttons(self) -> None:
        _set_dynamic_property(
            self.microphone_button,
            "active",
            bool(self.config.microphone_enabled),
        )
        _set_dynamic_property(
            self.speaker_button,
            "active",
            bool(self.config.speaker_enabled),
        )
        for button, enabled in (
            (self.microphone_button, self.config.microphone_enabled),
            (self.speaker_button, self.config.speaker_enabled),
        ):
            effect = button.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(button)
                button.setGraphicsEffect(effect)
            effect.setOpacity(1.0 if enabled else 0.38)

    def _toggle_audio_source(self, kind: str) -> None:
        if kind == "microphone":
            enabled = not self.config.microphone_enabled
            self.config.microphone_enabled = enabled
        else:
            enabled = not self.config.speaker_enabled
            self.config.speaker_enabled = enabled
        self.controller.set_audio_source_enabled(kind, enabled)
        self._refresh_audio_buttons()
        if self.controller.running and not (
            self.config.microphone_enabled or self.config.speaker_enabled
        ):
            self.controller.stop()

    def _set_auto_answer(self, enabled: bool) -> None:
        self.config.auto_generate = enabled
        self.controller.update_config(self.config)

    def _confirm_consent(self) -> bool:
        if self.config.consent_acknowledged:
            return True
        choice = QMessageBox.question(
            self,
            "Permission to transcribe",
            "I confirm that transcription is permitted and participants are informed where required.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return False
        self.config.consent_acknowledged = True
        self.controller.update_config(self.config)
        return True

    def toggle_session(self) -> None:
        if self.controller.running:
            self.controller.stop()
            return
        if not (self.config.microphone_enabled or self.config.speaker_enabled):
            self._show_error("Enable the microphone or meeting-audio button first.")
            return
        if not self._confirm_consent():
            return
        self.error_banner.hide()
        self.controller.start()

    def generate_answer(self) -> None:
        self.controller.ask(
            self.question_input.toPlainText(),
            self.config.answer_style,
        )

    def _clear_workspace(self) -> None:
        self.question_input.clear()
        self.answer_view.clear()
        self.answer_view.setToolTip("")
        self.error_banner.hide()

    def _show_transcript(self, speaker: str, text: str, is_question: bool) -> None:  # noqa: ARG002
        if is_question and speaker == "Interviewer":
            self.question_input.setPlainText(text)

    def _show_question(self, question: str) -> None:
        self.question_input.setPlainText(question)

    def _show_answer(self, question: str, answer: str, sources: object) -> None:
        self.question_input.setPlainText(question)
        self.answer_view.setPlainText(answer)
        source_tuple = tuple(str(source) for source in (sources or ()))
        self.answer_view.setToolTip(
            f"Grounded in: {', '.join(source_tuple)}"
            if source_tuple
            else "No matching context source"
        )
        self.error_banner.hide()

    def _show_status(self, message: str) -> None:
        self.session_button.setToolTip(message)

    def _show_transcribing(self, active: bool) -> None:
        self.transcription_indicator.setVisible(bool(active and self.controller.running))

    def _show_level(self, source: str, value: float) -> None:
        button = self.speaker_button if source == "Interviewer" else self.microphone_button
        _set_dynamic_property(button, "signal", value >= 0.035)

    def _show_error(self, message: str) -> None:
        self.error_banner.setText(message)
        self.error_banner.show()
        self.session_button.setToolTip(message)

    def _show_source_state(self, kind: str, available: bool, message: str) -> None:
        button = self.microphone_button if kind == "microphone" else self.speaker_button
        enabled = (
            self.config.microphone_enabled if kind == "microphone" else self.config.speaker_enabled
        )
        state = "connected" if available else ("retrying" if enabled and self.controller.running else "off")
        _set_dynamic_property(button, "sourceState", state)
        button.setToolTip(message)

    def _session_state(self, running: bool) -> None:
        self.session_button.setText("LIVE" if running else "START")
        self.session_button.setToolTip("Stop listening" if running else "Start listening")
        _set_dynamic_property(self.session_button, "running", running)
        if not running:
            self.transcription_indicator.hide()
            for button in (self.microphone_button, self.speaker_button):
                _set_dynamic_property(button, "signal", False)
                _set_dynamic_property(button, "sourceState", "off")
            self._refresh_history()

    def _refresh_history(self) -> None:
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        sessions = self.database.list_sessions(limit=4)
        if not sessions:
            empty = QLabel("No saved meetings yet")
            empty.setObjectName("EmptyHistory")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_layout.addWidget(empty)
            return
        for index, session in enumerate(sessions):
            row = QFrame()
            row.setObjectName("MeetingRow")
            row.setProperty("last", index == len(sessions) - 1)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(37, 0, 31, 0)
            layout.setSpacing(0)
            title = QLabel(session_display_title(session))
            title.setObjectName("MeetingTitle")
            title.setFixedWidth(219)
            layout.addWidget(title)
            layout.addSpacing(5)
            stamp = QLabel(session_display_time(session.started_at))
            stamp.setObjectName("MeetingTime")
            stamp.setFixedWidth(60)
            layout.addWidget(stamp)
            layout.addStretch()
            transcript = self._icon_button(
                object_name="MeetingTranscript",
                asset="meeting-transcript.png",
                icon_size=(25, 25),
            )
            transcript.setToolTip("View transcript")
            transcript.clicked.connect(partial(self._view_session_content, session.id, "transcript"))
            notes = self._icon_button(
                object_name="MeetingNotes",
                asset="meeting-notes.png",
                icon_size=(26, 26),
            )
            notes.setToolTip("View generated answers and notes")
            notes.clicked.connect(partial(self._view_session_content, session.id, "answers"))
            delete = self._icon_button(
                object_name="MeetingDelete",
                asset="meeting-delete.png",
                icon_size=(25, 25),
            )
            delete.setToolTip("Delete meeting")
            delete.clicked.connect(partial(self._delete_session, session.id))
            transcript.setFixedSize(25, 25)
            notes.setFixedSize(26, 26)
            delete.setFixedSize(25, 25)
            layout.addWidget(transcript)
            layout.addSpacing(1)
            layout.addWidget(notes)
            layout.addWidget(delete)
            self.history_layout.addWidget(row)

    def _view_session_content(self, session_id: int, mode: str) -> None:
        SessionContentDialog(self.database, session_id, mode, self).exec()

    def _delete_session(self, session_id: int) -> None:
        if QMessageBox.question(
            self,
            "Delete meeting",
            "Permanently delete this local meeting, transcript and generated answers?",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.database.delete_session(session_id)
        self._refresh_history()

    def check_updates(self) -> None:
        self._manual_update_check = True
        self.session_button.setText("CHECK")
        self.session_button.setToolTip("Checking for prxmpt updates…")
        self.updater.check_for_updates()

    def _automatic_update_check(self) -> None:
        if self.config.auto_check_updates:
            self.updater.check_for_updates()

    def _show_update_available(self, release: ReleaseInfo) -> None:
        self._available_release = release
        self._manual_update_check = False
        self._session_state(self.controller.running)
        self.settings_button.setToolTip(
            f"prxmpt {release.version} is available — open this menu to install"
        )
        _set_dynamic_property(self.settings_button, "updateAvailable", True)
        if self.tray:
            self.tray.showMessage(
                "prxmpt update available",
                f"Version {release.version} is ready. Open prxmpt settings to install it.",
                QSystemTrayIcon.MessageIcon.Information,
                8000,
            )

    def _show_no_update(self, current_version: str) -> None:
        if self._manual_update_check:
            QMessageBox.information(
                self,
                "prxmpt updates",
                f"prxmpt {current_version} is the latest published version.",
            )
        self._manual_update_check = False
        _set_dynamic_property(self.settings_button, "updateAvailable", False)
        self._session_state(self.controller.running)

    def _show_update_check_failed(self, message: str) -> None:
        if self._manual_update_check:
            self._show_error(message)
        self._manual_update_check = False
        self._session_state(self.controller.running)

    def _open_release_notes(self) -> None:
        if self._available_release and self._available_release.page_url:
            QDesktopServices.openUrl(QUrl(self._available_release.page_url))

    def _prompt_update_install(self) -> None:
        if not self._available_release:
            return
        if QMessageBox.question(
            self,
            "Install prxmpt update",
            f"Download and install prxmpt {self._available_release.version}?",
        ) == QMessageBox.StandardButton.Yes:
            self.session_button.setText("0%")
            self.updater.download(self._available_release)

    def _show_update_progress(self, percent: int) -> None:
        self.session_button.setText(f"{max(0, min(100, percent))}%")

    def _show_update_download_failed(self, message: str) -> None:
        self._show_error(f"Update failed safely: {message}")
        self._session_state(self.controller.running)

    def _install_downloaded_update(self, installer_path: str) -> None:
        if self.controller.running:
            self.controller.stop()
        if self.updater.launch_installer(installer_path):
            self._allow_quit = True
            self._cleanup()
            QTimer.singleShot(300, QApplication.instance().quit)

    def _toggle_drag_lock(self) -> None:
        self._drag_locked = not self._drag_locked
        self.config.popup_drag_locked = self._drag_locked
        self.controller.update_config(self.config)
        self._update_drag_button()

    def _update_drag_button(self) -> None:
        self.drag_button.setToolTip(
            "Unlock popup position" if self._drag_locked else "Lock popup position"
        )
        _set_dynamic_property(self.drag_button, "unlocked", not self._drag_locked)

    def _toggle_collapsed(self) -> None:
        if self._collapsed:
            self.body.show()
            self._designer_form.setFixedSize(DESIGN_WIDTH, DESIGN_HEIGHT)
            self.popup_frame.setFixedSize(DESIGN_WIDTH, DESIGN_HEIGHT)
            if self._graphics_scene is not None:
                self._graphics_scene.setSceneRect(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT)
            self.setFixedSize(*self._expanded_size)
            self.collapse_button.setToolTip("Collapse prxmpt to the title bar")
            self._collapsed = False
            return
        self._expanded_size = (self.width(), self.height())
        self.body.hide()
        self._designer_form.setFixedSize(DESIGN_WIDTH, COLLAPSED_HEIGHT)
        self.popup_frame.setFixedSize(DESIGN_WIDTH, COLLAPSED_HEIGHT)
        if self._graphics_scene is not None:
            self._graphics_scene.setSceneRect(0, 0, DESIGN_WIDTH, COLLAPSED_HEIGHT)
        self.setFixedSize(self.width(), round(COLLAPSED_HEIGHT * self._ui_scale))
        self.collapse_button.setToolTip("Expand prxmpt")
        self._collapsed = True

    def toggle_popup(self) -> None:
        if self.isVisible():
            self.minimize_to_tray()
        else:
            self._bring_to_front()

    def minimize_to_tray(self) -> None:
        self.hide()
        if self.tray and not self._tray_notice_shown:
            self.tray.showMessage(
                "prxmpt is still running",
                "Use the tray icon or Ctrl+Alt+O to reopen it.",
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )
            self._tray_notice_shown = True

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self._bring_to_front()

    def _bring_to_front(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_application(self) -> None:
        self._allow_quit = True
        self.close()
        QApplication.instance().quit()

    def _cleanup(self) -> None:
        if self._cleaned_up:
            return
        self._cleaned_up = True
        self.updater.shutdown()
        self.controller.shutdown()
        if self.tray:
            self.tray.hide()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._initial_geometry_applied:
            return
        self._initial_geometry_applied = True
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        width, height = self.width(), self.height()
        self.move(available.left() + (available.width() - width) // 2, available.top() + 12)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            not self._drag_locked
            and event.button() == Qt.MouseButton.LeftButton
            and self.header.geometry().contains(event.position().toPoint())
        ):
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            target = event.globalPosition().toPoint() - self._drag_origin
            screen = self.screen() or QApplication.primaryScreen()
            if screen:
                area = screen.availableGeometry()
                target.setX(max(area.left(), min(target.x(), area.right() - self.width() + 1)))
                target.setY(max(area.top(), min(target.y(), area.bottom() - self.height() + 1)))
            self.move(target)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_origin = None
        super().mouseReleaseEvent(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.header and not self._drag_locked:
            if (
                event.type() == QEvent.Type.MouseButtonPress
                and isinstance(event, QMouseEvent)
                and event.button() == Qt.MouseButton.LeftButton
            ):
                self._drag_origin = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
                return True
            if (
                event.type() == QEvent.Type.MouseMove
                and isinstance(event, QMouseEvent)
                and self._drag_origin is not None
                and event.buttons() & Qt.MouseButton.LeftButton
            ):
                self.move(event.globalPosition().toPoint() - self._drag_origin)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_origin = None
                return True
        return super().eventFilter(watched, event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._allow_quit:
            event.ignore()
            self.minimize_to_tray()
            return
        self._cleanup()
        event.accept()
