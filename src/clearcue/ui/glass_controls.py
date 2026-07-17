from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication, QFrame, QPushButton, QWidget

from clearcue.ui.skins import active_skin


class TactileIconButton(QPushButton):
    """Render the supplied artwork unchanged, adding only fast interaction feedback."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setFlat(True)
        self._hover_progress = 0.0
        self._press_progress = 0.0
        self._icon_rotation = 0.0
        self._hover_animation = self._animation(b"hoverProgress", 110)
        self._press_animation = self._animation(b"pressProgress", 75)

    def _animation(self, target: bytes, duration: int) -> QPropertyAnimation:
        animation = QPropertyAnimation(self, target, self)
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        return animation

    def _animate(self, animation: QPropertyAnimation, end: float) -> None:
        animation.stop()
        animation.setStartValue(
            self._hover_progress if animation is self._hover_animation else self._press_progress
        )
        animation.setEndValue(end)
        animation.start()

    def getHoverProgress(self) -> float:
        return self._hover_progress

    def setHoverProgress(self, value: float) -> None:
        self._hover_progress = float(value)
        self.update()

    hoverProgress = Property(float, getHoverProgress, setHoverProgress)

    def getPressProgress(self) -> float:
        return self._press_progress

    def setPressProgress(self, value: float) -> None:
        self._press_progress = float(value)
        self.update()

    pressProgress = Property(float, getPressProgress, setPressProgress)

    def setIconRotation(self, degrees: float) -> None:
        self._icon_rotation = float(degrees)
        self.update()

    def enterEvent(self, event) -> None:
        self._animate(self._hover_animation, 1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate(self._hover_animation, 0.0)
        self._animate(self._press_animation, 0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._animate(self._press_animation, 1.0)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._animate(self._press_animation, 0.0)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )

        active = self.property("active")
        opacity = 1.0
        if not self.isEnabled():
            opacity = 0.34
        elif active is False:
            opacity = 0.38
        painter.setOpacity(opacity)

        selected = bool(self.property("selected")) or bool(self.property("signal"))
        selected = selected or bool(self.property("updateAvailable"))
        selected = selected or bool(self.property("unlocked"))
        if self._hover_progress > 0.01 or selected or self.hasFocus():
            # Feedback is deliberately fill-only: no focus, selection or hover
            # stroke is drawn around the supplied artwork.
            resting_alpha = 14 if selected or self.hasFocus() else 0
            glow_alpha = resting_alpha + round(22 * self._hover_progress)
            painter.setPen(Qt.PenStyle.NoPen)
            accent = active_skin().rgba("accent", glow_alpha / 255)
            painter.setBrush(QColor(*accent))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 7, 7)

        if self.icon().isNull():
            return
        icon_size = self.iconSize()
        pixmap = self.icon().pixmap(icon_size)
        scale = 1.0 + 0.018 * self._hover_progress - 0.055 * self._press_progress
        offset_y = 0.9 * self._press_progress
        painter.save()
        painter.translate(QPointF(self.width() / 2.0, self.height() / 2.0 + offset_y))
        painter.rotate(self._icon_rotation)
        painter.scale(scale, scale)
        target = QRectF(
            -icon_size.width() / 2.0,
            -icon_size.height() / 2.0,
            icon_size.width(),
            icon_size.height(),
        )
        painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
        painter.restore()


class LogoToggleButton(TactileIconButton):
    """The unchanged prxmpt artwork acting as a tactile toggle and drag handle."""

    dragStarted = Signal(QPoint)
    dragMoved = Signal(QPoint)
    dragFinished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._drag_enabled = False
        self._press_global: QPoint | None = None
        self._dragging = False

    def setDragEnabled(self, enabled: bool) -> None:
        self._drag_enabled = bool(enabled)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        current = event.globalPosition().toPoint()
        if (
            self._drag_enabled
            and self._press_global is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            if not self._dragging and (
                current - self._press_global
            ).manhattanLength() >= QApplication.startDragDistance():
                self._dragging = True
                self.dragStarted.emit(self._press_global)
            if self._dragging:
                self.dragMoved.emit(current)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._press_global = None
            self.setDown(False)
            self._animate(self._press_animation, 0.0)
            self.dragFinished.emit()
            event.accept()
            return
        self._press_global = None
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        # Keep the subtle squeeze active while an unlocked logo drag travels
        # outside the original 104x56 hit area.
        if self._dragging:
            self._animate(self._hover_animation, 0.0)
            QPushButton.leaveEvent(self, event)
            return
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        if self.icon().isNull():
            return
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        icon_size = self.iconSize()
        pixmap = self.icon().pixmap(icon_size)
        scale = 1.0 - 0.018 * self._press_progress
        target = QRectF(
            -icon_size.width() / 2.0,
            -icon_size.height() / 2.0,
            icon_size.width(),
            icon_size.height(),
        )
        painter.translate(QPointF(self.width() / 2.0, self.height() / 2.0))
        painter.scale(scale, scale)
        if self._hover_progress > 0.01:
            painter.save()
            painter.setOpacity(0.075 * self._hover_progress)
            for offset in (
                QPointF(-1.4, 0.0),
                QPointF(1.4, 0.0),
                QPointF(0.0, -1.4),
                QPointF(0.0, 1.4),
            ):
                painter.drawPixmap(
                    target.translated(offset),
                    pixmap,
                    QRectF(pixmap.rect()),
                )
            painter.restore()
        painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))


class AudioLevelLamp(QWidget):
    """Small source lamp with fast attack and smooth decay from live audio RMS."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._display_level = 0.0
        self._source_active = True
        self._color = QColor("#1d99ef")
        self._level_animation = QPropertyAnimation(self, b"displayLevel", self)
        self._level_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def setColor(self, color: QColor | str) -> None:
        self._color = QColor(color)
        self.update()

    def setSourceActive(self, active: bool) -> None:
        self._source_active = bool(active)
        if not self._source_active:
            self.setLevel(0.0)
        self.update()

    def getDisplayLevel(self) -> float:
        return self._display_level

    def setDisplayLevel(self, value: float) -> None:
        self._display_level = min(1.0, max(0.0, float(value)))
        self.update()

    displayLevel = Property(float, getDisplayLevel, setDisplayLevel)

    def setLevel(self, value: float) -> None:
        raw = min(1.0, max(0.0, float(value))) if self._source_active else 0.0
        # Speech RMS is normally concentrated near the bottom of the 0..1
        # range. This curve keeps quiet speech visible without saturating loud
        # peaks immediately.
        target = min(1.0, raw / 0.18) ** 0.58
        self._level_animation.stop()
        self._level_animation.setDuration(
            48 if target >= self._display_level else 155
        )
        self._level_animation.setStartValue(self._display_level)
        self._level_animation.setEndValue(target)
        self._level_animation.start()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        level = self._display_level if self._source_active else 0.0
        if level > 0.01:
            glow = QRadialGradient(center, 8.5)
            glow_color = QColor(self._color)
            glow_color.setAlpha(round(45 + 125 * level))
            glow.setColorAt(0.0, glow_color)
            edge = QColor(self._color)
            edge.setAlpha(0)
            glow.setColorAt(1.0, edge)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1))
        core = QColor(self._color if self._source_active else QColor("#5f6669"))
        core.setAlpha(round(68 + 187 * level) if self._source_active else 45)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(core)
        radius = 4.4 + 0.5 * level
        painter.drawEllipse(center, radius, radius)


class GlassButton(QPushButton):
    """Compact model badge matching the black/brown pill in the SVG."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, rect.height() / 2.0, rect.height() / 2.0)
        skin = active_skin()
        painter.fillPath(path, QColor(*skin.rgba("base")))
        if self.underMouse() or self.isDown():
            highlight = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            highlight.setColorAt(0.0, QColor(255, 255, 255, 55))
            highlight.setColorAt(
                1.0,
                QColor(*skin.rgba("accent", 10 / 255)),
            )
            painter.fillPath(path, QBrush(highlight))
        font = self.font()
        font.setBold(True)
        painter.setFont(font)
        text_rect = rect.translated(0.0, 1.0 if self.isDown() else 0.0)
        painter.setPen(QColor(45, 24, 30, 210))
        for x, y in ((-0.55, 0.0), (0.55, 0.0), (0.0, -0.55), (0.0, 0.55)):
            painter.drawText(
                text_rect.translated(x, y),
                Qt.AlignmentFlag.AlignCenter,
                self.text(),
            )
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.text())


class TopBarBackdrop(QFrame):
    """Native recreation of the 720×58 SVG header and its lower green reflection."""

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.0, 8.99438, 720.0, 45.3586)
        path = QPainterPath()
        path.addRoundedRect(rect, 22.6793, 22.6793)
        skin = active_skin()
        painter.fillPath(path, QColor(*skin.rgba("base")))

        painter.save()
        painter.setClipPath(path)
        reflection = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        reflection.setColorAt(0.0, QColor(170, 199, 52, 0))
        reflection.setColorAt(0.72, QColor(170, 199, 52, 4))
        reflection.setColorAt(1.0, QColor(170, 199, 52, 78))
        painter.fillPath(path, QBrush(reflection))
        painter.restore()

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(*skin.rgba("base")), 1.0))
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 22.1793, 22.1793)
