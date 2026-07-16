from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QDir, QFile, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPixmap, QRegion
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QMainWindow,
    QWidget,
)
from PySide6.QtUiTools import QUiLoader

from clearcue.resources import resource_path


class ToggleSwitch(QCheckBox):
    """Compact switch that reuses the exact approved SVG-embedded on asset."""

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
    return rounded_rect_path(0, 0, 516, 46, 23, scale)


def audio_handler_mask(scale: float) -> QPainterPath:
    path = rounded_rect_path(0, 22, 110, 118, 55, scale)
    path.addPath(rounded_rect_path(118, 0, 398, 161, 58, scale))
    return path


def activity_buttons_mask(scale: float) -> QPainterPath:
    path = rounded_rect_path(0, 0, 91, 22, 11, scale)
    path.addPath(rounded_rect_path(98, 0, 93, 22, 11, scale))
    return path


def plot_popup_mask(scale: float) -> QPainterPath:
    return rounded_rect_path(0, 0, 516, 393, 58, scale)


def history_popup_mask(scale: float) -> QPainterPath:
    return rounded_rect_path(0, 0, 516, 390, 58, scale)


class PopupPanel(QMainWindow):
    """One independently hosted surface in the coordinated popup cluster."""

    def __init__(
        self,
        owner: QWidget,
        filename: str,
        design_size: tuple[int, int],
        scale: float,
        mask_factory: MaskFactory,
    ) -> None:
        super().__init__(owner)
        self.scale_factor = scale
        self.mask_factory = mask_factory
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
        self.apply_window_shape()

    def apply_window_shape(self) -> None:
        path = self.mask_factory(self.scale_factor)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
