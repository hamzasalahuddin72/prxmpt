from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QAbstractAnimation,
    QDir,
    QEasingCurve,
    QFile,
    QPropertyAnimation,
    QRectF,
    QSize,
    QTimer,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QRegion,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextOption,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QMainWindow,
    QScrollArea,
    QTextEdit,
    QWidget,
)
from PySide6.QtUiTools import QUiLoader

from clearcue.resources import resource_path
from clearcue.ui.glass_controls import (
    AudioLevelLamp,
    GlassButton,
    LogoToggleButton,
    TactileIconButton,
    TopBarBackdrop,
)
from clearcue.ui.popup_helpers import POPUP_CORNER_RADIUS


class ToggleSwitch(QCheckBox):
    """25 px switch that reuses the canonical radio-button artwork."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(25, 25)
        self._on_pixmap = QPixmap(str(resource_path("toggle-on.png")))

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isChecked() and not self._on_pixmap.isNull():
            painter.drawPixmap(self.rect(), self._on_pixmap)
            return
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#55575C"))
        painter.drawRoundedRect(0, 6, 25, 13, 7, 7)
        painter.setBrush(QColor("#D8D9DC"))
        painter.drawEllipse(0, 6, 13, 13)


class TypingIndicator(QWidget):
    """Low-cost animated dots shown only during active transcription."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.setInterval(230)
        self._timer.timeout.connect(self._advance)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def _advance(self) -> None:
        self._phase = (self._phase + 1) % 3
        self.update()

    def showEvent(self, event) -> None:
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for index, x in enumerate((5.0, 13.0, 21.0)):
            distance = (index - self._phase) % 3
            alpha = (255, 145, 75)[distance]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, alpha))
            painter.drawEllipse(QRectF(x - 2.2, 6.8, 4.4, 4.4))


class LiveTranscriptView(QTextEdit):
    """Single-line rich transcript with bold question-candidate spans."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setAcceptRichText(False)
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.document().setDocumentMargin(0)

    def set_transcript(
        self,
        committed: object,
        active_regular: str,
        active_question: str,
    ) -> None:
        document = self.document()
        document.clear()
        cursor = QTextCursor(document)
        normal = QTextCharFormat()
        normal.setForeground(QColor("#FFFFFF"))
        normal.setFontWeight(QFont.Weight.DemiBold)
        normal.setTextOutline(QPen(QColor(45, 24, 30, 185), 0.35))
        bold = QTextCharFormat(normal)
        bold.setFontWeight(QFont.Weight.Bold)
        has_text = False

        def append(text: str, emphasized: bool) -> None:
            nonlocal has_text
            cleaned = " ".join(str(text).split())
            if not cleaned:
                return
            if has_text:
                cursor.insertText(" ", normal)
            cursor.insertText(cleaned, bold if emphasized else normal)
            has_text = True

        for item in committed if isinstance(committed, (list, tuple)) else ():
            try:
                text, emphasized = item
            except (TypeError, ValueError):
                continue
            append(str(text), bool(emphasized))
        append(active_regular, False)
        append(active_question, True)
        self.setTextCursor(cursor)
        QTimer.singleShot(0, self._scroll_to_latest)

    def _scroll_to_latest(self) -> None:
        bar = self.horizontalScrollBar()
        bar.setValue(bar.maximum())


class ReadableTextHighlighter(QSyntaxHighlighter):
    """Apply a subtle dark edge to white popup text without changing content."""

    def __init__(self, document) -> None:
        super().__init__(document)
        self._format = QTextCharFormat()
        self._format.setForeground(QColor("#FFFFFF"))
        self._format.setFontWeight(QFont.Weight.DemiBold)
        self._format.setTextOutline(QPen(QColor(45, 24, 30, 185), 0.35))

    def highlightBlock(self, text: str) -> None:
        if text:
            self.setFormat(0, len(text), self._format)


class ReadableLabel(QLabel):
    """Draw small popup labels directly so scaled proxy widgets cannot clip them."""

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        text = self.text()
        if not text:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        font = self.font()
        font.setBold(True)
        painter.setFont(font)
        rect = QRectF(self.contentsRect())
        alignment = self.alignment()
        painter.setPen(QColor(45, 24, 30, 205))
        for x, y in ((-0.45, 0.0), (0.45, 0.0), (0.0, -0.45), (0.0, 0.45)):
            painter.drawText(rect.translated(x, y), alignment, text)
        painter.setPen(self.palette().windowText().color())
        painter.drawText(rect, alignment, text)


class LoadingSpinner(QWidget):
    """Rotate the supplied artwork only while answer generation is active."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = 0
        self._pixmap = QPixmap(str(resource_path("answer-loading.png")))
        self._timer = QTimer(self)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._advance)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def _advance(self) -> None:
        self._angle = (self._angle + 30) % 360
        self.update()

    def showEvent(self, event) -> None:
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        if self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        painter.translate(self.width() / 2.0, self.height() / 2.0)
        painter.rotate(self._angle)
        target = QRectF(
            -self.width() / 2.0,
            -self.height() / 2.0,
            self.width(),
            self.height(),
        )
        painter.drawPixmap(target, self._pixmap, QRectF(self._pixmap.rect()))


class SmoothScrollArea(QScrollArea):
    """Animate wheel movement while preserving precise trackpad deltas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scroll_animation = QPropertyAnimation(
            self.verticalScrollBar(),
            b"value",
            self,
        )
        self._scroll_animation.setDuration(145)
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def wheelEvent(self, event: QWheelEvent) -> None:
        bar = self.verticalScrollBar()
        if bar.maximum() <= bar.minimum():
            super().wheelEvent(event)
            return

        pixel_delta = event.pixelDelta().y()
        if pixel_delta:
            distance = -pixel_delta
        else:
            angle_delta = event.angleDelta().y()
            if not angle_delta:
                super().wheelEvent(event)
                return
            distance = round(-(angle_delta / 120.0) * 38)

        base = bar.value()
        if self._scroll_animation.state() == QAbstractAnimation.State.Running:
            end_value = self._scroll_animation.endValue()
            if end_value is not None:
                base = int(end_value)
        target = max(bar.minimum(), min(bar.maximum(), base + distance))
        self._scroll_animation.stop()
        self._scroll_animation.setStartValue(bar.value())
        self._scroll_animation.setEndValue(target)
        self._scroll_animation.start()
        event.accept()


class PrxmptUiLoader(QUiLoader):
    """Load editable Designer forms while preserving custom toggle widgets."""

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
        if class_name == "TypingIndicator":
            widget = TypingIndicator(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "LiveTranscriptView":
            widget = LiveTranscriptView(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "LoadingSpinner":
            widget = LoadingSpinner(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "SmoothScrollArea":
            widget = SmoothScrollArea(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "AudioLevelLamp":
            widget = AudioLevelLamp(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "LogoToggleButton":
            widget = LogoToggleButton(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "QLabel" and name in {
            "LiveLabel",
            "AutoAnswerLabel",
            "StealthLabel",
        }:
            widget = ReadableLabel(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "QPushButton":
            widget = GlassButton(parent) if name == "ModelBadge" else TactileIconButton(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "QFrame" and name == "PopupHeader":
            widget = TopBarBackdrop(parent)
            widget.setObjectName(name)
            return widget
        return super().createWidget(class_name, parent, name)


def load_popup_form(filename: str) -> QWidget:
    ui_path = resource_path(filename)
    ui_file = QFile(str(ui_path))
    if not ui_file.open(QFile.OpenModeFlag.ReadOnly):
        raise RuntimeError(f"Unable to open the editable UI form: {ui_path}")
    loader = PrxmptUiLoader()
    loader.setWorkingDirectory(QDir(str(Path(ui_path).parent)))
    try:
        form = loader.load(ui_file)
    finally:
        ui_file.close()
    if not isinstance(form, QWidget):
        raise RuntimeError(f"Unable to load {ui_path}: {loader.errorString()}")
    return form


def install_scaled_form(
    window: QMainWindow,
    filename: str,
    design_size: tuple[int, int],
    scale: float,
) -> tuple[QWidget, QGraphicsScene | None, QGraphicsView | None]:
    """Install a fixed Designer form, scaling the complete surface if required."""

    form = load_popup_form(filename)
    form.setFixedSize(*design_size)
    target_size = QSize(
        round(design_size[0] * scale),
        round(design_size[1] * scale),
    )
    window.setFixedSize(target_size)
    if scale >= 0.999:
        window.setCentralWidget(form)
        return form, None, None

    scene = QGraphicsScene(window)
    scene.setSceneRect(0, 0, *design_size)
    scene.addWidget(form)
    view = QGraphicsView(scene)
    view.setObjectName("PopupGraphicsView")
    view.setFrameShape(QFrame.Shape.NoFrame)
    view.setStyleSheet("background: transparent; border: 0; padding: 0;")
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    view.setRenderHints(
        QPainter.RenderHint.Antialiasing
        | QPainter.RenderHint.TextAntialiasing
        | QPainter.RenderHint.SmoothPixmapTransform
    )
    view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
    view.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    view.scale(scale, scale)
    window.setCentralWidget(view)
    return form, scene, view


def rounded_rect_path(
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
    scale: float,
) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(
        QRectF(x * scale, y * scale, width * scale, height * scale),
        radius * scale,
        radius * scale,
    )
    return path


MaskFactory = Callable[[float], QPainterPath]


def top_bar_mask(scale: float) -> QPainterPath:
    path = rounded_rect_path(
        0, 8.99438, 720, 45.3586, POPUP_CORNER_RADIUS, scale
    )
    # The logo's vector shadow deliberately rises above and below the bar.
    # Union only that central area so the outer window corners stay click-through.
    logo = QPainterPath()
    logo.addRect(QRectF(308 * scale, 8 * scale, 104 * scale, 50 * scale))
    return path.united(logo)


def prompt_screen_mask(scale: float) -> QPainterPath:
    return rounded_rect_path(0, 0, 720, 35, POPUP_CORNER_RADIUS, scale)


def feedback_window_mask(scale: float) -> QPainterPath:
    return rounded_rect_path(0, 0, 720, 260, POPUP_CORNER_RADIUS, scale)


def history_popup_mask(scale: float) -> QPainterPath:
    return rounded_rect_path(0, 0, 720, 164, POPUP_CORNER_RADIUS, scale)


class PopupPanel(QMainWindow):
    """One independently hosted surface in the coordinated popup cluster."""

    def __init__(
        self,
        owner: QWidget,
        filename: str,
        design_size: tuple[int, int],
        scale: float,
        mask_factory: MaskFactory,
        dynamic_height: bool = False,
    ) -> None:
        super().__init__(owner)
        self.scale_factor = scale
        self.mask_factory = mask_factory
        self.design_size = design_size
        self.dynamic_height = dynamic_height
        self._visible_design_height = float(design_size[1])
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.form, self.scene, self.graphics_view = install_scaled_form(
            self,
            filename,
            design_size,
            scale,
        )
        self._height_animation = QPropertyAnimation(
            self,
            b"visibleDesignHeight",
            self,
        )
        self._height_animation.setDuration(180)
        self._height_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.apply_window_shape()

    def apply_window_shape(self) -> None:
        if self.dynamic_height:
            path = rounded_rect_path(
                0,
                0,
                self.design_size[0],
                self._visible_design_height,
                POPUP_CORNER_RADIUS,
                self.scale_factor,
            )
        else:
            path = self.mask_factory(self.scale_factor)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def getVisibleDesignHeight(self) -> float:
        return self._visible_design_height

    def setVisibleDesignHeight(self, height: float) -> None:
        maximum = float(self.design_size[1])
        self._visible_design_height = max(1.0, min(maximum, float(height)))
        self.apply_window_shape()

    visibleDesignHeight = Property(
        float,
        getVisibleDesignHeight,
        setVisibleDesignHeight,
    )

    def set_visible_design_height(self, height: int, *, animated: bool) -> None:
        """Apply a new visible height, animating only an already-visible panel."""

        target = max(1.0, min(float(self.design_size[1]), float(height)))
        self._height_animation.stop()
        if not animated or not self.isVisible() or abs(target - self._visible_design_height) < 0.5:
            self.setVisibleDesignHeight(target)
            return
        self._height_animation.setStartValue(self._visible_design_height)
        self._height_animation.setEndValue(target)
        self._height_animation.start()
