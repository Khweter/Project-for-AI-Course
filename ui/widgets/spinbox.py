from __future__ import annotations
from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox, QStyle, QStyleOptionSpinBox
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen

from ui.theme import Colors


class _SpinIconMixin:

    def paintEvent(self, event):
        super().paintEvent(event)

        opt = QStyleOptionSpinBox()
        self.initStyleOption(opt)
        up_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_SpinBox, opt, QStyle.SubControl.SC_SpinBoxUp, self
        )
        down_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_SpinBox, opt, QStyle.SubControl.SC_SpinBoxDown, self
        )

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fg = QColor(Colors.TEXT_BRIGHT if self.isEnabled() else Colors.TEXT_DIM)
        pen = QPen(fg, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)

        if up_rect.isValid():
            cx, cy = up_rect.center().x() + 0.5, up_rect.center().y() + 0.5
            p.drawLine(QPointF(cx - 3.2, cy + 1.5), QPointF(cx, cy - 1.8))
            p.drawLine(QPointF(cx, cy - 1.8), QPointF(cx + 3.2, cy + 1.5))

        if down_rect.isValid():
            cx, cy = down_rect.center().x() + 0.5, down_rect.center().y() + 0.5
            p.drawLine(QPointF(cx - 3.2, cy - 1.5), QPointF(cx, cy + 1.8))
            p.drawLine(QPointF(cx, cy + 1.8), QPointF(cx + 3.2, cy - 1.5))

        p.end()


class CleanSpinBox(_SpinIconMixin, QSpinBox):
    pass


class CleanDoubleSpinBox(_SpinIconMixin, QDoubleSpinBox):
    pass
