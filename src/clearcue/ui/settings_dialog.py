from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from clearcue.audio.devices import list_input_devices, list_loopback_devices
from clearcue.config import AppConfig
from clearcue.intelligence.providers import GeminiProvider
from clearcue.security import (
    SecretStoreError,
    get_gemini_key,
    get_openai_key,
    set_gemini_key,
    set_openai_key,
)


class SettingsDialog(QDialog):
    gemini_test_finished = Signal(bool, str)

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("prxmpt Settings")
        self.resize(650, 640)
        self.original_config = config
        self.result_config = replace(config)
        self._test_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="prxmpt-gemini-test",
        )
        self.gemini_test_finished.connect(self._finish_gemini_test)
        self.finished.connect(
            lambda _result: self._test_executor.shutdown(
                wait=False,
                cancel_futures=True,
            )
        )

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        audio_tab = QWidget()
        audio_form = QFormLayout(audio_tab)
        self.speaker_combo = QComboBox()
        self.microphone_combo = QComboBox()
        refresh = QPushButton("Refresh devices")
        refresh.clicked.connect(self._load_devices)
        audio_form.addRow("Meeting/system audio", self.speaker_combo)
        audio_form.addRow("Your microphone", self.microphone_combo)
        audio_form.addRow("", refresh)
        note = QLabel(
            "Windows loopback captures meeting audio. The microphone uses the more "
            "driver-compatible PortAudio backend. VoiceMeeter devices appear here automatically."
        )
        note.setWordWrap(True)
        note.setObjectName("Muted")
        audio_form.addRow(note)
        tabs.addTab(audio_tab, "Audio")

        speech_tab = QWidget()
        speech_form = QFormLayout(speech_tab)
        self.whisper_model = QComboBox()
        self.whisper_model.setEditable(True)
        self.whisper_model.addItems(["tiny.en", "base.en", "small.en"])
        self.whisper_model.setCurrentText(config.whisper_model)
        self.whisper_device = QComboBox()
        self.whisper_device.addItem("CPU", "cpu")
        self.whisper_device.addItem("NVIDIA CUDA", "cuda")
        self._set_combo_data(self.whisper_device, config.whisper_device)
        self.compute_type = QComboBox()
        self.compute_type.addItems(["int8", "float16", "int8_float16", "float32"])
        self.compute_type.setCurrentText(config.whisper_compute_type)
        self.whisper_device.currentIndexChanged.connect(self._sync_compute_type)
        self._sync_compute_type()
        speech_form.addRow("Local Whisper model", self.whisper_model)
        speech_form.addRow("Processing device", self.whisper_device)
        speech_form.addRow("Compute type", self.compute_type)
        model_note = QLabel(
            "Performance default: tiny.en + CPU + int8. Use base.en for more accuracy. "
            "The Windows installer includes tiny.en; other selected models download once."
        )
        model_note.setWordWrap(True)
        model_note.setObjectName("Muted")
        speech_form.addRow(model_note)
        tabs.addTab(speech_tab, "Transcription")

        ai_tab = QWidget()
        ai_form = QFormLayout(ai_tab)
        self.provider = QComboBox()
        self.provider.addItem("Local grounded outline (no API)", "local")
        self.provider.addItem("Google Gemini API", "gemini")
        self.provider.addItem("OpenAI Responses API", "openai")
        self.provider.addItem("Ollama on this computer", "ollama")
        self._set_combo_data(self.provider, config.answer_provider)
        self.gemini_model = QComboBox()
        self.gemini_model.addItem("Quality — Gemini 3.5 Flash", "gemini-3.5-flash")
        self.gemini_model.addItem(
            "Fast — Gemini 3.1 Flash-Lite",
            "gemini-3.1-flash-lite",
        )
        self._set_combo_data(self.gemini_model, config.gemini_model)
        if self.gemini_model.currentData() != config.gemini_model:
            self.gemini_model.addItem(config.gemini_model, config.gemini_model)
            self._set_combo_data(self.gemini_model, config.gemini_model)
        self.gemini_api_key = QLineEdit()
        self.gemini_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_api_key.setPlaceholderText(
            "Stored securely in Windows Credential Manager"
        )
        try:
            self.gemini_api_key.setText(get_gemini_key())
        except SecretStoreError:
            pass
        self.gemini_test = QPushButton("Test Gemini connection")
        self.gemini_test.clicked.connect(self._test_gemini_connection)
        self.gemini_clear = QPushButton("Clear saved Gemini key")
        self.gemini_clear.clicked.connect(self._clear_gemini_key)
        gemini_key_link = QLabel(
            '<a href="https://aistudio.google.com/app/apikey">Create or view a '
            "Gemini API key in Google AI Studio</a>"
        )
        gemini_key_link.setOpenExternalLinks(True)
        gemini_key_link.setWordWrap(True)
        self.openai_model = QComboBox()
        self.openai_model.setEditable(True)
        self.openai_model.addItems(["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6"])
        self.openai_model.setCurrentText(config.openai_model)
        self.openai_api_key = QLineEdit()
        self.openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key.setPlaceholderText(
            "Stored securely in Windows Credential Manager"
        )
        try:
            self.openai_api_key.setText(get_openai_key())
        except SecretStoreError:
            pass
        self.ollama_url = QLineEdit(config.ollama_url)
        self.ollama_model = QLineEdit(config.ollama_model)
        self.answer_style = QComboBox()
        self.answer_style.addItem("Concise spoken answer", "concise")
        self.answer_style.addItem("Detailed answer", "detailed")
        self.answer_style.addItem("STAR behavioural answer", "star")
        self.answer_style.addItem("Technical explanation", "technical")
        self._set_combo_data(self.answer_style, config.answer_style)
        self.auto_generate = QCheckBox("Generate when an interviewer question is detected")
        self.auto_generate.setChecked(config.auto_generate)
        ai_form.addRow("Answer provider", self.provider)
        ai_form.addRow("Gemini mode", self.gemini_model)
        ai_form.addRow("Gemini API key", self.gemini_api_key)
        ai_form.addRow("", gemini_key_link)
        ai_form.addRow("", self.gemini_test)
        ai_form.addRow("", self.gemini_clear)
        ai_form.addRow("OpenAI model", self.openai_model)
        ai_form.addRow("OpenAI API key", self.openai_api_key)
        ai_form.addRow("Ollama address", self.ollama_url)
        ai_form.addRow("Ollama model", self.ollama_model)
        ai_form.addRow("Default style", self.answer_style)
        ai_form.addRow("", self.auto_generate)
        gemini_privacy = QLabel(
            "Gemini receives only the detected question and selected local context, never "
            "microphone audio. Google states that free-tier content may be used to improve "
            "its products. Free quotas and model availability can change."
        )
        gemini_privacy.setWordWrap(True)
        gemini_privacy.setObjectName("Muted")
        ai_form.addRow(gemini_privacy)
        tabs.addTab(ai_tab, "Answers")
        self.provider.currentIndexChanged.connect(self._sync_provider_fields)
        self._sync_provider_fields()

        updates_tab = QWidget()
        updates_form = QFormLayout(updates_tab)
        self.auto_check_updates = QCheckBox("Notify me when a stable prxmpt update is available")
        self.auto_check_updates.setChecked(config.auto_check_updates)
        updates_form.addRow("Automatic checks", self.auto_check_updates)
        updates_note = QLabel(
            "prxmpt checks the public GitHub Release feed without an account or token. "
            "Use the Updates button in the main window to check immediately. Installation "
            "always requires your confirmation."
        )
        updates_note.setWordWrap(True)
        updates_note.setObjectName("Muted")
        updates_form.addRow(updates_note)
        tabs.addTab(updates_tab, "Updates")

        privacy_tab = QWidget()
        privacy_form = QFormLayout(privacy_tab)
        self.save_transcripts = QCheckBox("Save session transcripts locally")
        self.save_transcripts.setChecked(config.save_transcripts)
        privacy_form.addRow("Session history", self.save_transcripts)
        privacy_note = QLabel(
            "Raw audio is never saved. API keys use Windows Credential Manager. "
            "Cloud providers receive only the "
            "selected question and retrieved context."
        )
        privacy_note.setWordWrap(True)
        privacy_note.setObjectName("Muted")
        privacy_form.addRow(privacy_note)
        tabs.addTab(privacy_tab, "Privacy")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._load_devices()

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _populate_device_combo(self, combo: QComboBox, devices, current_id: str) -> None:
        combo.clear()
        combo.addItem("Use current Windows default (recommended)", "")
        for device in devices:
            combo.addItem(device.label, device.id)
        index = combo.findData(current_id)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.setCurrentIndex(0)

    def _sync_compute_type(self) -> None:
        if self.whisper_device.currentData() == "cpu" and self.compute_type.currentText() in {
            "float16",
            "int8_float16",
        }:
            self.compute_type.setCurrentText("int8")

    def _sync_provider_fields(self) -> None:
        selected = str(self.provider.currentData() or "local")
        for widget in (
            self.gemini_model,
            self.gemini_api_key,
            self.gemini_test,
            self.gemini_clear,
        ):
            widget.setEnabled(selected == "gemini")
        self.openai_model.setEnabled(selected == "openai")
        self.openai_api_key.setEnabled(selected == "openai")
        self.ollama_url.setEnabled(selected == "ollama")
        self.ollama_model.setEnabled(selected == "ollama")

    def _clear_gemini_key(self) -> None:
        self.gemini_api_key.clear()
        self.gemini_api_key.setPlaceholderText(
            "The saved key will be removed when you click Save"
        )

    def _test_gemini_connection(self) -> None:
        key = self.gemini_api_key.text().strip()
        if not key:
            QMessageBox.warning(
                self,
                "Gemini connection",
                "Enter a Gemini API key first.",
            )
            return
        model = str(self.gemini_model.currentData() or "gemini-3.5-flash")
        self.gemini_test.setEnabled(False)
        self.gemini_test.setText("Testing…")

        future = self._test_executor.submit(
            GeminiProvider(key, model).generate,
            "Reply with only the single word: connected",
        )

        def complete(completed) -> None:
            try:
                completed.result()
                self.gemini_test_finished.emit(True, "Gemini is connected.")
            except Exception as exc:
                self.gemini_test_finished.emit(False, str(exc))

        future.add_done_callback(complete)

    def _finish_gemini_test(self, success: bool, message: str) -> None:
        self.gemini_test.setText("Test Gemini connection")
        self._sync_provider_fields()
        if success:
            QMessageBox.information(self, "Gemini connection", message)
        else:
            QMessageBox.warning(self, "Gemini connection", message)

    def _load_devices(self) -> None:
        try:
            self._populate_device_combo(
                self.speaker_combo, list_loopback_devices(), self.original_config.speaker_id
            )
            self._populate_device_combo(
                self.microphone_combo, list_input_devices(), self.original_config.microphone_id
            )
        except Exception as exc:
            self.speaker_combo.clear()
            self.microphone_combo.clear()
            self.speaker_combo.addItem("Audio devices unavailable", "")
            self.microphone_combo.addItem("Audio devices unavailable", "")
            self.speaker_combo.setToolTip(str(exc))

    def _save(self) -> None:
        try:
            set_gemini_key(self.gemini_api_key.text())
            set_openai_key(self.openai_api_key.text())
        except SecretStoreError as exc:
            QMessageBox.warning(self, "Credential storage", str(exc))
            return
        whisper_device = str(self.whisper_device.currentData() or "cpu")
        compute_type = self.compute_type.currentText()
        if whisper_device == "cpu" and compute_type not in {"int8", "float32"}:
            compute_type = "int8"
        self.result_config = replace(
            self.original_config,
            speaker_id=str(self.speaker_combo.currentData() or ""),
            microphone_id=str(self.microphone_combo.currentData() or ""),
            whisper_model=self.whisper_model.currentText().strip() or "tiny.en",
            whisper_device=whisper_device,
            whisper_compute_type=compute_type,
            answer_provider=str(self.provider.currentData()),
            gemini_model=str(
                self.gemini_model.currentData() or "gemini-3.5-flash"
            ),
            openai_model=self.openai_model.currentText().strip() or "gpt-5.6-luna",
            ollama_url=self.ollama_url.text().strip() or "http://127.0.0.1:11434",
            ollama_model=self.ollama_model.text().strip() or "qwen3:8b",
            answer_style=str(self.answer_style.currentData()),
            auto_generate=self.auto_generate.isChecked(),
            # Opacity is controlled by the top-bar popup and must survive an
            # unrelated Settings save.
            overlay_opacity=self.original_config.overlay_opacity,
            save_transcripts=self.save_transcripts.isChecked(),
            auto_check_updates=self.auto_check_updates.isChecked(),
        )
        self.accept()
