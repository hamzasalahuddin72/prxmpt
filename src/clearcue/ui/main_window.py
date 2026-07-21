from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from functools import partial

from PySide6.QtCore import QEvent, QObject, QPoint, QProcess, QSize, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDesktopServices,
    QIcon,
    QMouseEvent,
    QMoveEvent,
    QPixmap,
    QRegion,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from clearcue import __version__
from clearcue.config import AppConfig, ConfigStore
from clearcue.intelligence.model_catalog import (
    AvailableModel,
    ModelCatalog,
    discover_available_models,
)
from clearcue.resources import resource_path
from clearcue.services.session_controller import SessionController
from clearcue.services.updater import ReleaseInfo, UpdateService
from clearcue.storage.database import Database
from clearcue.ui.context_dialog import ContextDialog
from clearcue.ui.history_dialog import HistoryDialog
from clearcue.ui.glass_controls import (
    AudioLevelLamp,
    FocusMeetingRecord,
    LogoToggleButton,
    TactileIconButton,
)
from clearcue.ui.popup_cluster import (
    LiveTranscriptView,
    LoadingSpinner,
    PopupPanel,
    ReadableTextHighlighter,
    ToggleSwitch,
    TypingIndicator,
    feedback_window_mask,
    history_popup_mask,
    install_scaled_form,
    prompt_screen_mask,
    top_bar_mask,
)
from clearcue.ui.popup_helpers import (
    FEEDBACK_WINDOW_SIZE,
    HISTORY_POPUP_SIZE,
    PROMPT_SCREEN_SIZE,
    TOP_BAR_SIZE,
    PopupState,
    controls_toggle_target,
    history_toggle_target,
    plot_toggle_target,
    popup_cluster_positions,
    popup_cluster_size,
    popup_scale_for_screen,
    history_content_height,
    history_popup_height,
    session_display_datetime,
    session_display_duration,
    session_display_model,
    session_display_title,
)
from clearcue.ui.session_content_dialog import SessionContentDialog
from clearcue.ui.settings_dialog import SettingsDialog
from clearcue.ui.skins import available_skins


class HotkeyBridge(QObject):
    toggle_session = Signal()
    generate = Signal()
    toggle_overlay = Signal()


class ModelCatalogBridge(QObject):
    ready = Signal(int, object)


def _set_dynamic_property(widget: QWidget, name: str, value: object) -> None:
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class MainWindow(QMainWindow):
    """Top-bar owner and controller for the four independent popup surfaces."""

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
        self._popup_state = PopupState.TOP_ONLY
        self._initial_geometry_applied = False
        self._allow_quit = False
        self._cleaned_up = False
        self._tray_notice_shown = False
        self._syncing_cluster_position = False
        self._answer_snapshots: list[tuple[str, str, str]] = []
        self._answer_cursor = -1
        self._current_question = ""
        self._generation_active = False
        self._generation_question = ""
        self._generation_text = ""
        self._model_catalog = ModelCatalog(())
        self._model_catalog_loading = False
        self._model_catalog_request = 0
        self._history_rows: list[FocusMeetingRecord] = []
        self._hovered_history_row: FocusMeetingRecord | None = None
        self._model_catalog_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="prxmpt-model-catalog",
        )
        self._model_catalog_bridge = ModelCatalogBridge(self)
        self._model_catalog_bridge.ready.connect(self._finish_model_catalog_refresh)

        self.setWindowTitle(f"prxmpt {__version__}")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(self._make_app_icon())
        self._ui_scale = self._target_scale()

        self._build_ui()
        self._connect_signals()
        self._setup_tray()
        self._refresh_model_badge()
        self._refresh_audio_buttons()
        self._refresh_history()
        self._update_drag_button()
        self._apply_cluster_opacity()
        self._apply_window_shape()
        self._apply_popup_state(PopupState.TOP_ONLY)

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(6 * 60 * 60 * 1000)
        self.update_timer.timeout.connect(self._automatic_update_check)
        self.update_timer.start()
        if self.config.auto_check_updates:
            QTimer.singleShot(4000, self._automatic_update_check)
        QTimer.singleShot(700, self._refresh_available_models)

    @staticmethod
    def _make_app_icon() -> QIcon:
        return QIcon(str(resource_path("prxmpt.ico")))

    def _target_scale(self) -> float:
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return 1.0
        available = screen.availableGeometry()
        return popup_scale_for_screen(available.width(), available.height())

    @staticmethod
    def _required_child(form: QWidget, widget_type: type, object_name: str):
        widget = form.findChild(widget_type, object_name)
        if widget is None:
            raise RuntimeError(f"The popup Designer forms are missing {object_name}.")
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
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @staticmethod
    def _icon_button(
        object_name: str,
        asset: str,
        icon_size: tuple[int, int],
    ) -> TactileIconButton:
        button = TactileIconButton()
        button.setObjectName(object_name)
        MainWindow._configure_asset_button(button, asset, icon_size)
        return button

    def _build_ui(self) -> None:
        self._top_form, self._top_scene, self._top_view = install_scaled_form(
            self,
            "prxmpt-top-bar.ui",
            TOP_BAR_SIZE,
            self._ui_scale,
        )
        self.prompt_popup = PopupPanel(
            self,
            "prxmpt-prompt-screen.ui",
            PROMPT_SCREEN_SIZE,
            self._ui_scale,
            prompt_screen_mask,
        )
        self.feedback_popup = PopupPanel(
            self,
            "prxmpt-feedback-window.ui",
            FEEDBACK_WINDOW_SIZE,
            self._ui_scale,
            feedback_window_mask,
        )
        self.history_popup = PopupPanel(
            self,
            "prxmpt-history-popup.ui",
            HISTORY_POPUP_SIZE,
            self._ui_scale,
            history_popup_mask,
            dynamic_height=True,
        )
        for popup in self._subordinate_popups:
            popup.setWindowIcon(self.windowIcon())
            popup.hide()

        find = self._required_child
        self.header = find(self._top_form, QFrame, "PopupHeader")
        self.settings_button = find(self._top_form, QPushButton, "SettingsIcon")
        self.speaker_button = find(self._top_form, QPushButton, "SpeakerButton")
        self.microphone_button = find(
            self._top_form,
            QPushButton,
            "MicrophoneButton",
        )
        self.live_label = find(self._top_form, QLabel, "LiveLabel")
        self.live_indicator = find(self._top_form, QLabel, "LiveIndicator")
        self.live_button = find(self._top_form, QPushButton, "LiveButton")
        self.brand = find(self._top_form, LogoToggleButton, "PopupBrand")
        self.drag_button = find(self._top_form, QPushButton, "DragIcon")
        self.opacity_button = find(self._top_form, QPushButton, "OpacityButton")
        self.microphone_lamp = find(
            self._top_form,
            AudioLevelLamp,
            "MicrophoneLevelLamp",
        )
        self.speaker_lamp = find(
            self._top_form,
            AudioLevelLamp,
            "SpeakerLevelLamp",
        )
        self.close_button = find(self._top_form, QPushButton, "PopupClose")

        prompt_form = self.prompt_popup.form
        self.question_input = find(
            prompt_form,
            LiveTranscriptView,
            "QuestionInput",
        )
        self.ask_button = find(prompt_form, QPushButton, "AnswerButton")
        self.transcription_indicator = find(
            prompt_form,
            TypingIndicator,
            "TranscriptionIndicator",
        )
        self.clear_button = find(prompt_form, QPushButton, "ClearButton")
        self.error_banner = find(prompt_form, QLabel, "PopupError")
        self.plot_toggle_button = find(
            prompt_form,
            QPushButton,
            "PlotToggleButton",
        )
        self.history_toggle_button = find(
            prompt_form,
            QPushButton,
            "HistoryToggleButton",
        )

        feedback_form = self.feedback_popup.form
        self.answer_view = find(feedback_form, QPlainTextEdit, "AnswerView")
        self.answer_view.viewport().setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
        )
        self._answer_text_highlighter = ReadableTextHighlighter(
            self.answer_view.document()
        )
        self.error_mirror = find(feedback_form, QLabel, "PopupErrorMirror")
        self.answer_loading_spinner = find(
            feedback_form,
            LoadingSpinner,
            "AnswerLoadingSpinner",
        )
        self.model_badge = find(feedback_form, QPushButton, "ModelBadge")
        self.previous_answer_button = find(
            feedback_form,
            QPushButton,
            "PreviousAnswerButton",
        )
        self.next_answer_button = find(
            feedback_form,
            QPushButton,
            "NextAnswerButton",
        )
        self.auto_answer_switch = find(
            feedback_form,
            ToggleSwitch,
            "AutoAnswerSwitch",
        )
        self.stealth_switch = find(feedback_form, ToggleSwitch, "StealthSwitch")
        auto_label = find(feedback_form, QLabel, "AutoAnswerLabel")
        stealth_label = find(feedback_form, QLabel, "StealthLabel")

        history_form = self.history_popup.form
        self.history_card = find(history_form, QFrame, "HistoryCard")
        self.history_scroll = find(history_form, QScrollArea, "HistoryScroll")
        self.history_contents = find(history_form, QWidget, "HistoryContents")
        history_layout = self.history_contents.layout()
        if not isinstance(history_layout, QVBoxLayout):
            raise RuntimeError("The history popup is missing HistoryLayout.")
        self.history_layout = history_layout

        for button in (self.microphone_button, self.speaker_button):
            button.setObjectName("AudioSourceButton")
            button.setProperty("topBarControl", True)
        auto_label.setObjectName("ToggleLabel")
        stealth_label.setObjectName("ToggleLabel")

        for button, asset, size in (
            (self.settings_button, "settings.png", (25, 25)),
            (self.drag_button, "drag-lock.png", (25, 25)),
            (self.opacity_button, "opacity-button.png", (25, 25)),
            (self.close_button, "exit.png", (25, 25)),
            (self.microphone_button, "microphone.png", (25, 25)),
            (self.speaker_button, "speaker.png", (25, 25)),
            (self.history_toggle_button, "history-toggle-button.png", (21, 25)),
            (self.plot_toggle_button, "ghost-writer-button.png", (25, 25)),
            (self.clear_button, "clear-button.png", (16, 25)),
            (self.ask_button, "answer-button.png", (25, 25)),
            (self.previous_answer_button, "answer-navigation.png", (25, 25)),
            (self.next_answer_button, "answer-navigation.png", (25, 25)),
        ):
            self._configure_asset_button(button, asset, size)
        if isinstance(self.previous_answer_button, TactileIconButton):
            self.previous_answer_button.setIconRotation(180)
        self._configure_asset_button(
            self.brand,
            "prxmpt-logo.png",
            (104, 56),
        )
        self.microphone_lamp.setColor("#ff383c")
        self.speaker_lamp.setColor("#1d99ef")
        self._live_on_pixmap = QPixmap(str(resource_path("live-button.png")))
        self.live_indicator.setScaledContents(True)
        self.transcription_indicator.hide()
        self.error_banner.hide()
        self.error_mirror.hide()
        self.answer_loading_spinner.hide()
        self.session_button = self.live_button
        self._refresh_answer_navigation()
        self._refresh_live_indicator()

        self.header.installEventFilter(self)
        self.settings_button.setToolTip("Settings, profile, context and updates")
        self.settings_button.clicked.connect(self._show_control_menu)
        self.opacity_button.setToolTip("Adjust popup opacity")
        self.opacity_button.clicked.connect(self._show_opacity_menu)
        self.drag_button.clicked.connect(self._toggle_drag_lock)
        self.brand.clicked.connect(self._toggle_controls)
        self.brand.dragStarted.connect(self._start_brand_drag)
        self.brand.dragMoved.connect(self._move_brand_drag)
        self.brand.dragFinished.connect(self._finish_brand_drag)
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
        self.plot_toggle_button.clicked.connect(self._toggle_plot_popup)
        self.history_toggle_button.clicked.connect(self._toggle_history_popup)
        self.previous_answer_button.setToolTip("Previous generated answer")
        self.previous_answer_button.clicked.connect(
            partial(self._browse_answer, -1)
        )
        self.next_answer_button.setToolTip("Next generated answer")
        self.next_answer_button.clicked.connect(partial(self._browse_answer, 1))
        self.model_badge.setToolTip("Choose an available answer model")
        self.model_badge.clicked.connect(self._show_model_menu)
        self.auto_answer_switch.setChecked(self.config.auto_generate)
        self.auto_answer_switch.setToolTip(
            "Generate an answer when a question is detected"
        )
        self.auto_answer_switch.toggled.connect(self._set_auto_answer)
        self.stealth_switch.setToolTip("Reserved for a future prxmpt feature")

    @property
    def _subordinate_popups(self) -> tuple[PopupPanel, ...]:
        return (
            self.prompt_popup,
            self.feedback_popup,
            self.history_popup,
        )

    def _apply_window_shape(self) -> None:
        path = top_bar_mask(self._ui_scale)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _connect_signals(self) -> None:
        self.controller.transcript_ready.connect(self._show_transcript)
        self.controller.live_transcript_changed.connect(self._show_live_transcript)
        self.controller.question_ready.connect(self._show_question)
        self.controller.answer_ready.connect(self._show_answer)
        self.controller.answer_started.connect(self._show_answer_started)
        self.controller.answer_delta.connect(self._show_answer_delta)
        self.controller.answer_failed.connect(self._show_answer_failed)
        self.controller.clarification_needed.connect(self._show_clarification)
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
        skins = menu.addMenu("Skins")
        for skin in available_skins():
            action = skins.addAction(skin.name)
            action.setCheckable(True)
            action.setChecked(skin.id == self.config.skin_id)
            action.triggered.connect(
                partial(self._choose_skin, skin.id, skin.name)
            )
        menu.addSeparator()
        settings = menu.addAction("Settings")
        settings.triggered.connect(self.open_settings)
        context = menu.addAction("Profiles and context")
        context.triggered.connect(self.open_context)
        history = menu.addAction("Full meeting history")
        history.triggered.connect(self._open_full_history)
        menu.addSeparator()
        if self._available_release:
            update = menu.addAction(
                f"Install prxmpt {self._available_release.version}"
            )
            update.triggered.connect(self._prompt_update_install)
            notes = menu.addAction("Open release notes")
            notes.triggered.connect(self._open_release_notes)
        else:
            update = menu.addAction("Check for updates")
            update.triggered.connect(self.check_updates)
        menu.addSeparator()
        quit_action = menu.addAction("Quit prxmpt")
        quit_action.triggered.connect(self.quit_application)
        menu.exec(
            self.mapToGlobal(
                QPoint(
                    round(520 * self._ui_scale),
                    round(TOP_BAR_SIZE[1] * self._ui_scale),
                )
            )
        )

    def _choose_skin(
        self,
        skin_id: str,
        skin_name: str,
        checked: bool = False,
    ) -> None:
        del checked
        if skin_id == self.config.skin_id:
            return
        choice = QMessageBox.warning(
            self,
            "Apply prxmpt skin",
            f"Apply {skin_name}? prxmpt must restart to finish changing the skin.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return

        previous_skin = self.config.skin_id
        previous_opacity = self.config.overlay_opacity
        self.config.skin_id = skin_id
        if skin_id in {"azure_knight", "rose_quartz"}:
            # The solid-color presets start at full window opacity. The user
            # can still adjust the normal opacity slider after the restart.
            self.config.overlay_opacity = 1.0
        self.controller.update_config(self.config)
        arguments = (
            list(sys.argv[1:])
            if getattr(sys, "frozen", False)
            else ["-m", "clearcue.main", *sys.argv[1:]]
        )
        result = QProcess.startDetached(sys.executable, arguments)
        started = bool(result[0] if isinstance(result, tuple) else result)
        if not started:
            self.config.skin_id = previous_skin
            self.config.overlay_opacity = previous_opacity
            self.controller.update_config(self.config)
            QMessageBox.critical(
                self,
                "Skin restart failed",
                "prxmpt could not restart, so the previous skin was kept.",
            )
            return

        self._allow_quit = True
        self._cleanup()
        QApplication.instance().quit()

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
        self._refresh_available_models()
        self._refresh_audio_buttons()
        self._apply_cluster_opacity()

    def _open_full_history(self) -> None:
        HistoryDialog(self.database, self).exec()
        self._refresh_history()

    def _refresh_model_badge(self) -> None:
        full_model = "Local grounded outline"
        if self.config.answer_provider == "gemini":
            full_model = self.config.gemini_model
            model = (
                "gem-lite"
                if "lite" in self.config.gemini_model.lower()
                else "gem-3.5"
            )
        elif self.config.answer_provider == "openai":
            model = self.config.openai_model
            full_model = model
            if model.startswith("gpt-5.6"):
                model = "gpt-5.6"
        elif self.config.answer_provider == "ollama":
            model = self.config.ollama_model
            full_model = model
        else:
            model = "local"
        self.model_badge.setText(model[:10])
        self.model_badge.setToolTip(
            f"Answer provider: {full_model}. Click to choose an available model."
        )

    def _refresh_available_models(self) -> None:
        self._model_catalog_request += 1
        request_id = self._model_catalog_request
        self._model_catalog_loading = True
        config = replace(self.config)
        future = self._model_catalog_executor.submit(
            discover_available_models,
            config,
        )

        def complete(completed) -> None:
            try:
                catalog = completed.result()
            except Exception:
                catalog = ModelCatalog((AvailableModel("local", "local", "Grounded outline"),))
            self._model_catalog_bridge.ready.emit(request_id, catalog)

        future.add_done_callback(complete)

    def _finish_model_catalog_refresh(
        self,
        request_id: int,
        catalog: object,
    ) -> None:
        if request_id != self._model_catalog_request:
            return
        self._model_catalog_loading = False
        if isinstance(catalog, ModelCatalog):
            self._model_catalog = catalog

    def _show_model_menu(self) -> None:
        menu = QMenu(self)
        if self._model_catalog_loading and not self._model_catalog.models:
            checking = menu.addAction("Checking available models…")
            checking.setEnabled(False)
        else:
            active = (self.config.answer_provider, self._configured_model_id())
            provider_labels = {
                "gemini": "Google Gemini",
                "openai": "OpenAI",
                "ollama": "Ollama",
                "local": "Offline",
            }
            for provider in ("gemini", "openai", "ollama", "local"):
                choices = [
                    model
                    for model in self._model_catalog.models
                    if model.provider == provider
                ]
                if not choices:
                    continue
                section = menu.addMenu(provider_labels[provider])
                for choice in choices:
                    action = section.addAction(choice.label)
                    action.setCheckable(True)
                    action.setChecked(choice.key == active)
                    action.setToolTip(choice.model_id)
                    action.triggered.connect(
                        partial(
                            self._select_answer_model,
                            choice.provider,
                            choice.model_id,
                        )
                    )
        menu.addSeparator()
        refresh = menu.addAction(
            "Checking…" if self._model_catalog_loading else "Refresh available models"
        )
        refresh.setEnabled(not self._model_catalog_loading)
        refresh.triggered.connect(self._refresh_available_models)
        configure = menu.addAction("Configure API keys…")
        configure.triggered.connect(self.open_settings)
        menu.exec(
            self.model_badge.mapToGlobal(
                QPoint(0, self.model_badge.height())
            )
        )

    def _configured_model_id(self) -> str:
        if self.config.answer_provider == "gemini":
            return self.config.gemini_model
        if self.config.answer_provider == "openai":
            return self.config.openai_model
        if self.config.answer_provider == "ollama":
            return self.config.ollama_model
        return "local"

    def _select_answer_model(
        self,
        provider: str,
        model_id: str,
        checked: bool = False,
    ) -> None:
        del checked
        if (provider, model_id) not in {
            model.key for model in self._model_catalog.models
        }:
            return
        self.config.answer_provider = provider
        if provider == "gemini":
            self.config.gemini_model = model_id
        elif provider == "openai":
            self.config.openai_model = model_id
        elif provider == "ollama":
            self.config.ollama_model = model_id
        self.controller.update_config(self.config)
        self._refresh_model_badge()
        self._show_status(f"Answer model changed to {model_id}")

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
        self.microphone_lamp.setSourceActive(
            bool(self.config.microphone_enabled)
        )
        self.speaker_lamp.setSourceActive(bool(self.config.speaker_enabled))

    def _refresh_live_indicator(self) -> None:
        running = bool(self.controller.running)
        has_error = bool(self.live_button.property("error"))
        if running and not has_error and not self._live_on_pixmap.isNull():
            self.live_indicator.setPixmap(self._live_on_pixmap)
        else:
            self.live_indicator.clear()
        _set_dynamic_property(self.live_indicator, "running", running)
        _set_dynamic_property(self.live_indicator, "error", has_error)
        _set_dynamic_property(self.live_label, "running", running)

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

    def _show_opacity_menu(self) -> None:
        menu = QMenu(self)
        panel = QWidget(menu)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 7, 10, 8)
        layout.setSpacing(4)
        label = QLabel(f"Opacity  {round(self.config.overlay_opacity * 100)}%")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(45, 100)
        slider.setValue(round(self.config.overlay_opacity * 100))
        slider.setFixedWidth(190)

        def preview(value: int) -> None:
            label.setText(f"Opacity  {value}%")
            opacity = value / 100.0
            self.setWindowOpacity(opacity)
            for popup in self._subordinate_popups:
                popup.setWindowOpacity(opacity)

        slider.valueChanged.connect(preview)
        layout.addWidget(label)
        layout.addWidget(slider)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        menu.exec(
            self.mapToGlobal(
                QPoint(
                    round(475 * self._ui_scale),
                    round(TOP_BAR_SIZE[1] * self._ui_scale),
                )
            )
        )
        self.config.overlay_opacity = slider.value() / 100.0
        self.controller.update_config(self.config)
        self._apply_cluster_opacity()

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
        self.error_mirror.hide()
        _set_dynamic_property(self.live_button, "error", False)
        self._refresh_live_indicator()
        self.controller.start()

    def generate_answer(self) -> None:
        self.controller.ask(
            self._current_question,
            self.config.answer_style,
        )

    def _clear_workspace(self) -> None:
        self.controller.cancel_answer()
        self.controller.clear_live_transcript()
        self.question_input.clear()
        self._current_question = ""
        self._generation_active = False
        self._generation_question = ""
        self._generation_text = ""
        self.answer_loading_spinner.hide()
        self.answer_view.clear()
        self.answer_view.setToolTip("")
        self.error_banner.hide()
        self.error_mirror.hide()
        _set_dynamic_property(self.live_button, "error", False)
        self._refresh_live_indicator()
        self._answer_cursor = len(self._answer_snapshots) - 1
        self._refresh_answer_navigation()

    def _show_transcript(self, speaker: str, text: str, is_question: bool) -> None:
        # The prompt surface is driven by live_transcript_changed so it can
        # preserve the full conversation and independently style a forming
        # question. This compatibility signal remains useful to other views.
        del speaker, text, is_question

    def _show_live_transcript(
        self,
        committed: object,
        active_regular: str,
        active_question: str,
    ) -> None:
        parts = tuple(
            (str(text), bool(emphasized))
            for text, emphasized in (committed or ())
        )
        self.question_input.set_transcript(
            parts,
            active_regular,
            active_question,
        )

    def _show_question(self, question: str) -> None:
        self._current_question = question

    def _show_answer_started(self, question: str) -> None:
        self._current_question = question
        self._generation_active = True
        self._generation_question = question
        self._generation_text = ""
        self._answer_cursor = len(self._answer_snapshots)
        self.answer_view.clear()
        self.answer_view.setToolTip("Generating answer…")
        self.answer_loading_spinner.show()
        self._refresh_answer_navigation()
        self.error_banner.hide()
        self.error_mirror.hide()
        self._apply_popup_state(PopupState.PLOT)

    def _show_answer_delta(self, question: str, delta: str) -> None:
        if not self._generation_active or question != self._generation_question:
            return
        self._generation_text += delta
        self.answer_loading_spinner.hide()
        if self._answer_cursor != len(self._answer_snapshots):
            return
        cursor = self.answer_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(delta)
        self.answer_view.setTextCursor(cursor)
        self.answer_view.ensureCursorVisible()

    def _show_answer(self, question: str, answer: str, sources: object) -> None:
        self._current_question = question
        self._generation_active = False
        self._generation_question = ""
        self._generation_text = ""
        self.answer_loading_spinner.hide()
        self.answer_view.setPlainText(answer)
        source_tuple = tuple(str(source) for source in (sources or ()))
        tooltip = (
            f"Grounded in: {', '.join(source_tuple)}"
            if source_tuple
            else "No matching context source"
        )
        self.answer_view.setToolTip(tooltip)
        snapshot = (question, answer, tooltip)
        if not self._answer_snapshots or self._answer_snapshots[-1] != snapshot:
            self._answer_snapshots.append(snapshot)
        self._answer_cursor = len(self._answer_snapshots) - 1
        self._refresh_answer_navigation()
        self.error_banner.hide()
        self.error_mirror.hide()
        self._apply_popup_state(PopupState.PLOT)

    def _refresh_answer_navigation(self) -> None:
        self.previous_answer_button.setEnabled(self._answer_cursor > 0)
        maximum = (
            len(self._answer_snapshots)
            if self._generation_active
            else len(self._answer_snapshots) - 1
        )
        self.next_answer_button.setEnabled(
            0 <= self._answer_cursor < maximum
        )

    def _browse_answer(self, direction: int) -> None:
        maximum = (
            len(self._answer_snapshots)
            if self._generation_active
            else len(self._answer_snapshots) - 1
        )
        if maximum < 0:
            return
        target = self._answer_cursor + direction
        target = max(0, min(maximum, target))
        self._answer_cursor = target
        if self._generation_active and target == len(self._answer_snapshots):
            self.answer_view.setPlainText(self._generation_text)
            self.answer_view.setToolTip("Generating answer…")
            self.answer_loading_spinner.setVisible(not self._generation_text)
        else:
            _question, answer, tooltip = self._answer_snapshots[target]
            self.answer_view.setPlainText(answer)
            self.answer_view.setToolTip(tooltip)
            self.answer_loading_spinner.hide()
        self.error_banner.hide()
        self.error_mirror.hide()
        self._refresh_answer_navigation()
        self._apply_popup_state(PopupState.PLOT)

    def _show_status(self, message: str) -> None:
        self.session_button.setToolTip(message)

    def _show_transcribing(self, active: bool) -> None:
        visible = bool(active and self.controller.running)
        self.transcription_indicator.setVisible(visible)
        _set_dynamic_property(self.live_button, "transcribing", visible)

    def _show_level(self, source: str, value: float) -> None:
        lamp = (
            self.speaker_lamp if source == "Interviewer" else self.microphone_lamp
        )
        lamp.setLevel(value)

    def _show_error(self, message: str) -> None:
        self.error_banner.setText(message)
        self.error_mirror.setText(message)
        self.error_banner.show()
        self.error_mirror.show()
        self.session_button.setToolTip(message)
        _set_dynamic_property(self.live_button, "error", True)
        self._refresh_live_indicator()
        if self.isVisible() and self._popup_state is PopupState.TOP_ONLY:
            self._apply_popup_state(PopupState.CONTROLS)

    def _show_answer_failed(self, message: str) -> None:
        del message
        self._generation_active = False
        self.answer_loading_spinner.hide()
        self._answer_cursor = len(self._answer_snapshots) - 1
        self._refresh_answer_navigation()

    def _show_clarification(self, question: str, message: str) -> None:
        """Present a gate decision without pretending it is a generated answer."""

        self._current_question = question
        self._generation_active = False
        self._generation_question = ""
        self._generation_text = ""
        self.answer_loading_spinner.hide()
        self.answer_view.setPlainText(f"Clarification needed\n\n{message}")
        self.answer_view.setToolTip("No answer provider was called for this transcript.")
        self._answer_cursor = len(self._answer_snapshots) - 1
        self._refresh_answer_navigation()
        self.error_banner.hide()
        self.error_mirror.hide()
        self._apply_popup_state(PopupState.PLOT)

    def _show_source_state(self, kind: str, available: bool, message: str) -> None:
        button = (
            self.microphone_button if kind == "microphone" else self.speaker_button
        )
        enabled = (
            self.config.microphone_enabled
            if kind == "microphone"
            else self.config.speaker_enabled
        )
        state = (
            "connected"
            if available
            else ("retrying" if enabled and self.controller.running else "off")
        )
        _set_dynamic_property(button, "sourceState", state)
        lamp = self.microphone_lamp if kind == "microphone" else self.speaker_lamp
        lamp.setSourceActive(bool(enabled and (available or not self.controller.running)))
        button.setToolTip(message)

    def _session_state(self, running: bool) -> None:
        self.session_button.setToolTip(
            "Stop listening" if running else "Start listening"
        )
        _set_dynamic_property(self.session_button, "running", running)
        self._refresh_live_indicator()
        if running:
            _set_dynamic_property(self.session_button, "error", False)
            self._refresh_live_indicator()
            return
        self.transcription_indicator.hide()
        _set_dynamic_property(self.session_button, "transcribing", False)
        for button, lamp, enabled in (
            (
                self.microphone_button,
                self.microphone_lamp,
                self.config.microphone_enabled,
            ),
            (
                self.speaker_button,
                self.speaker_lamp,
                self.config.speaker_enabled,
            ),
        ):
            lamp.setLevel(0.0)
            lamp.setSourceActive(bool(enabled))
            _set_dynamic_property(button, "sourceState", "off")
        self._refresh_history()

    def _refresh_history(self) -> None:
        self._history_rows.clear()
        self._hovered_history_row = None
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        sessions = self.database.list_sessions(limit=100)
        self._history_target_height = history_popup_height(len(sessions))
        self.history_popup.set_visible_design_height(
            self._history_target_height,
            animated=True,
        )
        self.history_contents.setMinimumHeight(history_content_height(len(sessions)))
        if not sessions:
            empty = QLabel("No saved meetings yet")
            empty.setObjectName("EmptyHistory")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setFixedHeight(34)
            self.history_layout.addWidget(empty)
            self.history_layout.addStretch()
            return

        for index, session in enumerate(sessions):
            row = FocusMeetingRecord()
            row.setObjectName("MeetingRow")
            row.setProperty("last", index == len(sessions) - 1)
            row.setFixedHeight(34)
            row.hoverChanged.connect(partial(self._focus_history_row, row))
            self._history_rows.append(row)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 0, 9, 0)
            layout.setSpacing(0)
            title = QLabel(session_display_title(session))
            title.setObjectName("MeetingTitle")
            title.setFixedWidth(146)
            layout.addWidget(title)
            stamp = QLabel(session_display_datetime(session.started_at))
            stamp.setObjectName("MeetingTime")
            stamp.setFixedWidth(222)
            stamp.setToolTip(stamp.text())
            layout.addWidget(stamp)
            duration = QLabel(
                session_display_duration(session.started_at, session.ended_at)
            )
            duration.setObjectName("MeetingDuration")
            duration.setFixedWidth(119)
            layout.addWidget(duration)
            model = QLabel(session_display_model(session.model_used))
            model.setObjectName("MeetingModel")
            model.setToolTip(session.model_used or "Local answer provider")
            layout.addWidget(model, 1)
            transcript = self._icon_button(
                "MeetingTranscript",
                "meeting-transcript.png",
                (25, 25),
            )
            transcript.setToolTip("View transcript")
            transcript.clicked.connect(
                partial(self._view_session_content, session.id, "transcript")
            )
            notes = self._icon_button(
                "MeetingNotes",
                "meeting-notes.png",
                (25, 25),
            )
            notes.setToolTip("View generated answers and notes")
            notes.clicked.connect(
                partial(self._view_session_content, session.id, "answers")
            )
            delete = self._icon_button(
                "MeetingDelete",
                "meeting-delete.png",
                (25, 25),
            )
            delete.setToolTip("Delete meeting")
            delete.clicked.connect(partial(self._delete_session, session.id))
            transcript.setFixedSize(25, 25)
            notes.setFixedSize(25, 25)
            delete.setFixedSize(25, 25)
            layout.addWidget(transcript)
            layout.addSpacing(2)
            layout.addWidget(notes)
            layout.addSpacing(2)
            layout.addWidget(delete)
            self.history_layout.addWidget(row)
        self.history_layout.addStretch()

    def _focus_history_row(
        self,
        hovered_row: FocusMeetingRecord,
        hovered: bool,
    ) -> None:
        if hovered:
            self._hovered_history_row = hovered_row
            for row in self._history_rows:
                row.setDimmed(row is not hovered_row)
            return
        if self._hovered_history_row is not hovered_row:
            return
        self._hovered_history_row = None
        for row in self._history_rows:
            row.setDimmed(False)

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
        self.settings_button.setToolTip("Checking for prxmpt updates…")
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
        self.settings_button.setToolTip("Settings, profile, context and updates")
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
            self.settings_button.setToolTip("Downloading prxmpt update: 0%")
            self.updater.download(self._available_release)

    def _show_update_progress(self, percent: int) -> None:
        safe_percent = max(0, min(100, percent))
        self.settings_button.setToolTip(
            f"Downloading prxmpt update: {safe_percent}%"
        )

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
        self.brand.setDragEnabled(not self._drag_locked)

    def _start_brand_drag(self, press_global: QPoint) -> None:
        if self._drag_locked:
            return
        self._drag_origin = press_global - self.frameGeometry().topLeft()

    def _move_brand_drag(self, current_global: QPoint) -> None:
        if self._drag_locked or self._drag_origin is None:
            return
        target = current_global - self._drag_origin
        self.move(self._clamped_top_left(target))

    def _finish_brand_drag(self) -> None:
        self._drag_origin = None

    def _toggle_controls(self) -> None:
        self._apply_popup_state(controls_toggle_target(self._popup_state))

    def _toggle_plot_popup(self) -> None:
        self._apply_popup_state(plot_toggle_target(self._popup_state))

    def _toggle_history_popup(self) -> None:
        target = history_toggle_target(self._popup_state)
        if target is PopupState.HISTORY:
            self._refresh_history()
            desired_height = self._history_target_height
            self.history_popup.set_visible_design_height(
                history_popup_height(1),
                animated=False,
            )
            self._apply_popup_state(target)

            def expand_history() -> None:
                if self._popup_state is PopupState.HISTORY:
                    self.history_popup.set_visible_design_height(
                        desired_height,
                        animated=True,
                    )

            QTimer.singleShot(0, expand_history)
            return
        self._apply_popup_state(target)

    def _apply_popup_state(self, state: PopupState) -> None:
        self._popup_state = state
        self.feedback_popup.hide()
        self.history_popup.hide()
        if state is PopupState.TOP_ONLY:
            self.prompt_popup.hide()
        else:
            self.prompt_popup.show()
            if state is PopupState.PLOT:
                self.feedback_popup.show()
            elif state is PopupState.HISTORY:
                self.history_popup.show()
        _set_dynamic_property(
            self.plot_toggle_button,
            "selected",
            state is PopupState.PLOT,
        )
        _set_dynamic_property(
            self.history_toggle_button,
            "selected",
            state is PopupState.HISTORY,
        )
        self.brand.setToolTip(
            "Show audio controls"
            if state is PopupState.TOP_ONLY
            else "Hide all popup controls"
        )
        self._position_cluster()
        self._raise_visible_popups()

    def _position_cluster(self) -> None:
        if self._syncing_cluster_position:
            return
        self._syncing_cluster_position = True
        try:
            positions = popup_cluster_positions(
                self.x(),
                self.y(),
                self._ui_scale,
            )
            self.prompt_popup.move(*positions["prompt"])
            self.feedback_popup.move(*positions["feedback"])
            self.history_popup.move(*positions["history"])
        finally:
            self._syncing_cluster_position = False

    def _raise_visible_popups(self) -> None:
        if not self.isVisible():
            return
        self.raise_()
        for popup in self._subordinate_popups:
            if popup.isVisible():
                popup.raise_()

    def _apply_cluster_opacity(self) -> None:
        opacity = min(1.0, max(0.45, float(self.config.overlay_opacity)))
        self.setWindowOpacity(opacity)
        for popup in self._subordinate_popups:
            popup.setWindowOpacity(opacity)

    def _clamped_top_left(self, target: QPoint) -> QPoint:
        screen = QApplication.screenAt(target) or self.screen() or QApplication.primaryScreen()
        if not screen:
            return target
        area = screen.availableGeometry()
        cluster_width, cluster_height = popup_cluster_size(
            self._popup_state,
            self._ui_scale,
        )
        target.setX(
            max(area.left(), min(target.x(), area.right() - cluster_width + 1))
        )
        target.setY(
            max(area.top(), min(target.y(), area.bottom() - cluster_height + 1))
        )
        return target

    def toggle_popup(self) -> None:
        if self.isVisible():
            self.minimize_to_tray()
        else:
            self._bring_to_front()

    def minimize_to_tray(self) -> None:
        for popup in self._subordinate_popups:
            popup.hide()
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
        self._popup_state = PopupState.TOP_ONLY
        self.show()
        self._apply_popup_state(PopupState.TOP_ONLY)
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
        self._model_catalog_request += 1
        self._model_catalog_executor.shutdown(wait=False, cancel_futures=True)
        self.controller.shutdown()
        for popup in self._subordinate_popups:
            popup.close()
        if self.tray:
            self.tray.hide()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._initial_geometry_applied:
            self._initial_geometry_applied = True
            screen = self.screen() or QApplication.primaryScreen()
            if screen:
                available = screen.availableGeometry()
                width = self.width()
                self.move(
                    available.left() + (available.width() - width) // 2,
                    available.top() + 12,
                )
        self._position_cluster()

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        self._position_cluster()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            not self._drag_locked
            and event.button() == Qt.MouseButton.LeftButton
            and self.header.geometry().contains(event.position().toPoint())
        ):
            self._drag_origin = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            target = event.globalPosition().toPoint() - self._drag_origin
            self.move(self._clamped_top_left(target))
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
                target = event.globalPosition().toPoint() - self._drag_origin
                self.move(self._clamped_top_left(target))
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
