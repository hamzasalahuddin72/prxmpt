from __future__ import annotations

from dataclasses import replace

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
from clearcue.security import SecretStoreError, get_openai_key, set_openai_key


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ClearCue Settings")
        self.resize(610, 570)
        self.original_config = config
        self.result_config = replace(config)

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
            "Direct Windows WASAPI loopback is used. If VoiceMeeter is installed, "
            "its virtual devices appear in these lists automatically."
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
        speech_form.addRow("Local Whisper model", self.whisper_model)
        speech_form.addRow("Processing device", self.whisper_device)
        speech_form.addRow("Compute type", self.compute_type)
        model_note = QLabel(
            "Performance default: tiny.en + CPU + int8. Use base.en for more accuracy. "
            "The selected model downloads once on first use."
        )
        model_note.setWordWrap(True)
        model_note.setObjectName("Muted")
        speech_form.addRow(model_note)
        tabs.addTab(speech_tab, "Transcription")

        ai_tab = QWidget()
        ai_form = QFormLayout(ai_tab)
        self.provider = QComboBox()
        self.provider.addItem("Local grounded outline (no API)", "local")
        self.provider.addItem("OpenAI Responses API", "openai")
        self.provider.addItem("Ollama on this computer", "ollama")
        self._set_combo_data(self.provider, config.answer_provider)
        self.openai_model = QComboBox()
        self.openai_model.setEditable(True)
        self.openai_model.addItems(["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6"])
        self.openai_model.setCurrentText(config.openai_model)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("Stored securely in Windows Credential Manager")
        try:
            self.api_key.setText(get_openai_key())
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
        ai_form.addRow("OpenAI model", self.openai_model)
        ai_form.addRow("OpenAI API key", self.api_key)
        ai_form.addRow("Ollama address", self.ollama_url)
        ai_form.addRow("Ollama model", self.ollama_model)
        ai_form.addRow("Default style", self.answer_style)
        ai_form.addRow("", self.auto_generate)
        tabs.addTab(ai_tab, "Answers")

        privacy_tab = QWidget()
        privacy_form = QFormLayout(privacy_tab)
        self.save_transcripts = QCheckBox("Save session transcripts locally")
        self.save_transcripts.setChecked(config.save_transcripts)
        privacy_form.addRow("Session history", self.save_transcripts)
        privacy_note = QLabel(
            "Raw audio is never saved. API keys use Windows Credential Manager. "
            "The performance overlay is opaque. Cloud providers receive only the "
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
            set_openai_key(self.api_key.text())
        except SecretStoreError as exc:
            QMessageBox.warning(self, "Credential storage", str(exc))
            return
        self.result_config = replace(
            self.original_config,
            speaker_id=str(self.speaker_combo.currentData() or ""),
            microphone_id=str(self.microphone_combo.currentData() or ""),
            whisper_model=self.whisper_model.currentText().strip() or "tiny.en",
            whisper_device=str(self.whisper_device.currentData()),
            whisper_compute_type=self.compute_type.currentText(),
            answer_provider=str(self.provider.currentData()),
            openai_model=self.openai_model.currentText().strip() or "gpt-5.6-luna",
            ollama_url=self.ollama_url.text().strip() or "http://127.0.0.1:11434",
            ollama_model=self.ollama_model.text().strip() or "qwen3:8b",
            answer_style=str(self.answer_style.currentData()),
            auto_generate=self.auto_generate.isChecked(),
            overlay_opacity=1.0,
            save_transcripts=self.save_transcripts.isChecked(),
        )
        self.accept()
