from __future__ import annotations
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QPushButton, QSlider, QLabel,
)
from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygonF, QPainterPath
import math

from core.trace import StepEvent
from ui.theme import Colors, SPACING


class PlaybackController(QObject):
    step_applied = pyqtSignal(int, object)
    position_changed = pyqtSignal(int, int)
    state_changed = pyqtSignal(bool)
    reset_done = pyqtSignal()
    finished = pyqtSignal()

    TICK_MS = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events: list[StepEvent] = []
        self._index: int = 0
        self._playing: bool = False
        self._speed_sps: int = 30
        self._accumulator: float = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._on_tick)

    @property
    def total_steps(self) -> int:
        return len(self._events)

    @property
    def current_index(self) -> int:
        return self._index

    @property
    def is_playing(self) -> bool:
        return self._playing

    def set_events(self, events: list[StepEvent]):
        self.pause()
        self._events = list(events)
        self._index = 0
        self._accumulator = 0.0
        self.reset_done.emit()
        self.position_changed.emit(0, len(self._events))

    def set_speed(self, steps_per_sec: int):
        self._speed_sps = max(1, steps_per_sec)

    def play(self):
        if not self._events or self._playing:
            return
        if self._index >= len(self._events):
            self.reset()
        self._playing = True
        self._accumulator = 0.0
        self._timer.start()
        self.state_changed.emit(True)

    def pause(self):
        if not self._playing:
            return
        self._playing = False
        self._timer.stop()
        self.state_changed.emit(False)

    def set_playing(self, playing: bool):
        if playing:
            self.play()
        else:
            self.pause()

    def reset(self):
        self.pause()
        self._index = 0
        self._accumulator = 0.0
        self.reset_done.emit()
        self.position_changed.emit(0, len(self._events))

    def step_forward(self):
        self.pause()
        if self._index < len(self._events):
            ev = self._events[self._index]
            self._index += 1
            self.step_applied.emit(self._index, ev)
            self.position_changed.emit(self._index, len(self._events))
            if self._index >= len(self._events):
                self.finished.emit()

    def step_backward(self):
        self.pause()
        if self._index > 0:
            self.seek(self._index - 1)

    def seek(self, target: int):
        self.pause()
        target = max(0, min(target, len(self._events)))
        self.reset_done.emit()
        self._index = 0
        for i in range(target):
            self._index = i + 1
            self.step_applied.emit(self._index, self._events[i])
        self.position_changed.emit(self._index, len(self._events))

    def _on_tick(self):
        if not self._playing or self._index >= len(self._events):
            self.pause()
            if self._index >= len(self._events) and self._events:
                self.finished.emit()
            return

        self._accumulator += (self._speed_sps * self.TICK_MS) / 1000.0
        steps = int(self._accumulator)
        if steps <= 0:
            return
        self._accumulator -= steps

        for _ in range(steps):
            if self._index >= len(self._events):
                break
            ev = self._events[self._index]
            self._index += 1
            self.step_applied.emit(self._index, ev)

        self.position_changed.emit(self._index, len(self._events))
        if self._index >= len(self._events):
            self.pause()
            self.finished.emit()


class IconButton(QPushButton):

    def __init__(self, icon_type: str, size: int = 30, primary: bool = False, parent=None):
        super().__init__(parent)
        self._icon_type = icon_type
        self._primary = primary
        self._hovered = False
        self.setFixedSize(size, size)
        self.setObjectName("icon-btn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def set_icon_type(self, icon_type: str):
        self._icon_type = icon_type
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        if self._primary:
            bg = QColor(Colors.ACCENT_HOVER if self._hovered else Colors.ACCENT)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawEllipse(1, 1, w - 2, h - 2)
            fg = QColor("#ffffff")
        else:
            if self._hovered and self.isEnabled():
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(Colors.BG_HOVER))
                p.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)
            fg = QColor(Colors.ACCENT if self._hovered and self.isEnabled() else Colors.TEXT_BRIGHT)
            if not self.isEnabled():
                fg = QColor(Colors.TEXT_DIM)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fg)

        cx, cy = w / 2, h / 2
        s = min(w, h) * 0.30

        match self._icon_type:
            case "play":
                p.drawPolygon(QPolygonF([
                    QPointF(cx - s * 0.45, cy - s * 0.9),
                    QPointF(cx - s * 0.45, cy + s * 0.9),
                    QPointF(cx + s * 0.95, cy),
                ]))

            case "pause":
                bw = max(2.5, s * 0.38)
                p.drawRoundedRect(int(cx - s * 0.65), int(cy - s * 0.85), int(bw), int(s * 1.7), 1, 1)
                p.drawRoundedRect(int(cx + s * 0.22), int(cy - s * 0.85), int(bw), int(s * 1.7), 1, 1)

            case "reset":
                pen = QPen(fg, 1.8)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawArc(int(cx - s * 0.85), int(cy - s * 0.85), int(s * 1.7), int(s * 1.7), 40 * 16, 280 * 16)
                p.setBrush(fg)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawPolygon(QPolygonF([
                    QPointF(cx + s * 0.35, cy - s * 1.05),
                    QPointF(cx + s * 1.0, cy - s * 0.55),
                    QPointF(cx + s * 0.35, cy - s * 0.15),
                ]))

            case "step_fwd":
                p.drawPolygon(QPolygonF([
                    QPointF(cx - s * 0.65, cy - s * 0.75),
                    QPointF(cx - s * 0.65, cy + s * 0.75),
                    QPointF(cx + s * 0.3, cy),
                ]))
                p.drawRect(int(cx + s * 0.45), int(cy - s * 0.75), max(2, int(s * 0.25)), int(s * 1.5))

            case "step_back":
                p.drawPolygon(QPolygonF([
                    QPointF(cx + s * 0.65, cy - s * 0.75),
                    QPointF(cx + s * 0.65, cy + s * 0.75),
                    QPointF(cx - s * 0.3, cy),
                ]))
                p.drawRect(int(cx - s * 0.7), int(cy - s * 0.75), max(2, int(s * 0.25)), int(s * 1.5))

            case "moon":
                outer = QPainterPath()
                outer.addEllipse(QPointF(cx, cy), s * 0.95, s * 0.95)
                cut = QPainterPath()
                cut.addEllipse(QPointF(cx + s * 0.42, cy - s * 0.32), s * 0.78, s * 0.78)
                p.drawPath(outer.subtracted(cut))

            case "sun":
                p.drawEllipse(QPointF(cx, cy), s * 0.48, s * 0.48)
                p.setPen(QPen(fg, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                for i in range(8):
                    ang = i * (math.pi / 4.0)
                    p.drawLine(
                        QPointF(cx + math.cos(ang) * s * 0.72, cy + math.sin(ang) * s * 0.72),
                        QPointF(cx + math.cos(ang) * s * 1.05, cy + math.sin(ang) * s * 1.05),
                    )

        p.end()


class PlaybackBar(QFrame):

    step_forward = pyqtSignal()
    step_backward = pyqtSignal()
    play_toggled = pyqtSignal(bool)
    speed_changed = pyqtSignal(int)
    scrubber_moved = pyqtSignal(int)
    reset_requested = pyqtSignal()
    zoom_in_requested = pyqtSignal()
    zoom_out_requested = pyqtSignal()
    zoom_reset_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("playback-bar")
        self.setFixedHeight(52)
        self._playing = False
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(SPACING)

        self.btn_reset = IconButton("reset", size=30)
        self.btn_reset.setToolTip("Reset")
        self.btn_step_back = IconButton("step_back", size=30)
        self.btn_step_back.setToolTip("Step Backward")
        self.btn_play = IconButton("play", size=34, primary=True)
        self.btn_play.setToolTip("Play / Pause")
        self.btn_step_fwd = IconButton("step_fwd", size=30)
        self.btn_step_fwd.setToolTip("Step Forward")

        self.btn_reset.clicked.connect(self.reset_requested)
        self.btn_step_back.clicked.connect(self.step_backward)
        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_step_fwd.clicked.connect(self.step_forward)

        for btn in (self.btn_reset, self.btn_step_back, self.btn_play, self.btn_step_fwd):
            layout.addWidget(btn)

        self.scrubber = QSlider(Qt.Orientation.Horizontal)
        self.scrubber.setRange(0, 0)
        self.scrubber.valueChanged.connect(self.scrubber_moved)
        layout.addWidget(self.scrubber, stretch=1)

        self.lbl_step = QLabel("0 / 0")
        self.lbl_step.setObjectName("mono-badge")
        self.lbl_step.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_step.setMinimumWidth(82)
        layout.addWidget(self.lbl_step)

        speed_lbl = QLabel("Speed")
        speed_lbl.setObjectName("dim")
        layout.addWidget(speed_lbl)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 120)
        self.speed_slider.setValue(30)
        self.speed_slider.setFixedWidth(96)
        self.speed_slider.valueChanged.connect(self.speed_changed)
        layout.addWidget(self.speed_slider)

        self.lbl_speed = QLabel("30 sps")
        self.lbl_speed.setObjectName("mono-badge")
        self.lbl_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_speed.setFixedWidth(58)
        self.speed_slider.valueChanged.connect(lambda v: self.lbl_speed.setText(f"{v} sps"))
        layout.addWidget(self.lbl_speed)

        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setObjectName("zoom-btn")
        self.btn_zoom_out.setFixedSize(26, 26)
        self.btn_zoom_out.setToolTip("Zoom Out (Ctrl+-)")
        self.btn_zoom_out.clicked.connect(self.zoom_out_requested)

        self.btn_zoom_fit = QPushButton("Fit")
        self.btn_zoom_fit.setObjectName("zoom-btn")
        self.btn_zoom_fit.setFixedHeight(26)
        self.btn_zoom_fit.setToolTip("Reset Zoom (Ctrl+0)")
        self.btn_zoom_fit.clicked.connect(self.zoom_reset_requested)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setObjectName("zoom-btn")
        self.btn_zoom_in.setFixedSize(26, 26)
        self.btn_zoom_in.setToolTip("Zoom In (Ctrl++)")
        self.btn_zoom_in.clicked.connect(self.zoom_in_requested)

        layout.addWidget(self.btn_zoom_out)
        layout.addWidget(self.btn_zoom_fit)
        layout.addWidget(self.btn_zoom_in)

    def _toggle_play(self):
        self.set_playing_state(not self._playing)
        self.play_toggled.emit(self._playing)

    def set_playing_state(self, playing: bool):
        self._playing = playing
        self.btn_play.set_icon_type("pause" if playing else "play")

    def set_range(self, total: int):
        self.scrubber.blockSignals(True)
        self.scrubber.setRange(0, max(0, total))
        self.scrubber.blockSignals(False)
        self.set_position(0, total)

    def set_position(self, pos: int, total: int | None = None):
        if total is None:
            total = self.scrubber.maximum()
        self.scrubber.blockSignals(True)
        self.scrubber.setValue(pos)
        self.scrubber.blockSignals(False)
        self.lbl_step.setText(f"{pos} / {total}")
