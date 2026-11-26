from __future__ import annotations
from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt, QPoint, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush

from ui.theme import Colors


class ZoomableGraphicsView(QGraphicsView):

    ZOOM_STEP = 1.15
    MIN_ZOOM = 0.25
    MAX_ZOOM = 10.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor(Colors.BG_PRIMARY)))
        self.setStyleSheet("border: none;")

        self._zoom_factor: float = 1.0
        self._user_zoomed: bool = False
        self._panning: bool = False
        self._pan_start: QPoint = QPoint()

    def fit_scene(self, rect: QRectF | None = None):
        if rect is None:
            rect = self.sceneRect()
        if rect.isNull():
            return
        self.resetTransform()
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_factor = 1.0
        self._user_zoomed = False

    def zoom_in(self):
        self._apply_zoom(self.ZOOM_STEP)

    def zoom_out(self):
        self._apply_zoom(1.0 / self.ZOOM_STEP)

    def reset_zoom(self):
        self.fit_scene()

    def refresh_theme(self):
        self.setBackgroundBrush(QBrush(QColor(Colors.BG_PRIMARY)))

    def _apply_zoom(self, factor: float):
        new_zoom = self._zoom_factor * factor
        if new_zoom < self.MIN_ZOOM or new_zoom > self.MAX_ZOOM:
            return
        self._zoom_factor = new_zoom
        self._user_zoomed = True
        self.scale(factor, factor)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        factor = self.ZOOM_STEP if delta > 0 else 1.0 / self.ZOOM_STEP
        self._apply_zoom(factor)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._user_zoomed and not self.sceneRect().isNull():
            self.fit_scene(self.sceneRect())

    def mousePressEvent(self, event):
        is_pan_btn = event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton
            and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        )
        if is_pan_btn:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)
