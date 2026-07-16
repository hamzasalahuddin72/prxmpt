from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class OverlayWindow(QWidget):
    regenerate_requested = Signal()
    main_window_requested = Signal()

    def __init__(self, opacity: float = 1.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Overlay")
        self.setWindowTitle("prxmpt Overlay")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        # The performance build stays opaque and avoids translucent-window
        # composition, which is expensive on some integrated GPUs.
        self.setWindowOpacity(1.0)
        self.resize(620, 430)
        self._drag_origin: QPoint | None = None
        self._locked = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setObjectName("OverlayCard")
        frame.setStyleSheet(
            """
            QFrame#OverlayCard { background: #000000; border: 2px solid #ffffff; }
            QLabel { color: #ffffff; background: #000000; }
            QLabel#OverlayMuted { color: #c8c8c8; }
            QPlainTextEdit { background: #000000; border: 2px solid #ffffff;
                             padding: 8px; color: #ffffff; }
            QPushButton { background: #000000; border: 2px solid #ffffff;
                          padding: 5px 9px; color: #ffffff; }
            QPushButton:hover { background: #ffffff; color: #000000; }
            """
        )
        root.addWidget(frame)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 16)

        header = QHBoxLayout()
        brand = QLabel("CLEARCUE")
        brand.setStyleSheet("font-weight: 800; color: #ffff00;")
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("OverlayMuted")
        header.addWidget(brand)
        header.addWidget(self.status_label)
        header.addStretch()

        self.lock_button = QPushButton("Lock")
        self.lock_button.setToolTip("Lock the overlay position")
        self.lock_button.clicked.connect(self._toggle_lock)
        close = QPushButton("×")
        close.setToolTip("Hide overlay")
        close.clicked.connect(self.hide)
        for button in (self.lock_button, close):
            button.setFixedHeight(28)
            header.addWidget(button)
        layout.addLayout(header)

        self.question_label = QLabel("Detected questions will appear here.")
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet("font-size: 12pt; font-weight: 650; padding: 4px 2px;")
        layout.addWidget(self.question_label)

        self.answer_view = QPlainTextEdit()
        self.answer_view.setReadOnly(True)
        self.answer_view.setPlaceholderText("Your grounded coaching answer will appear here.")
        layout.addWidget(self.answer_view, 1)

        footer = QHBoxLayout()
        self.sources_label = QLabel("")
        self.sources_label.setObjectName("OverlayMuted")
        footer.addWidget(self.sources_label, 1)
        regenerate = QPushButton("Regenerate")
        regenerate.clicked.connect(self.regenerate_requested)
        copy = QPushButton("Copy")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.answer_view.toPlainText()))
        open_main = QPushButton("Open app")
        open_main.clicked.connect(self.main_window_requested)
        footer.addWidget(regenerate)
        footer.addWidget(copy)
        footer.addWidget(open_main)
        layout.addLayout(footer)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_question(self, question: str) -> None:
        self.question_label.setText(question)

    def set_answer(self, question: str, answer: str, sources: tuple[str, ...]) -> None:
        self.set_question(question)
        self.answer_view.setPlainText(answer)
        self.sources_label.setText(
            f"Sources: {', '.join(sources)}" if sources else "No matching profile source"
        )

    def _toggle_lock(self) -> None:
        self._locked = not self._locked
        self.lock_button.setText("Unlock" if self._locked else "Lock")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._locked and event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_origin = None
        super().mouseReleaseEvent(event)
