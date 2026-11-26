from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from ui.theme import Colors


class LoadingSplash(QWidget):

    finished = pyqtSignal()

    STEPS = [
        (15, "Initializing core state-space engine..."),
        (35, "Registering search algorithms..."),
        (55, "Loading problem presets & heuristics..."),
        (78, "Preparing interactive canvases..."),
        (100, "Launching Project for AI..."),
    ]

    def __init__(self, interval_ms: int = 650, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(440, 230)

        self._step_idx = 0
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._advance)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {Colors.BG_SECONDARY}; "
            f"border: 1px solid {Colors.BORDER_LIGHT}; border-radius: 12px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 26, 28, 24)
        cl.setSpacing(10)

        accent_bar = QFrame()
        accent_bar.setFixedSize(44, 4)
        accent_bar.setStyleSheet(
            f"background-color: {Colors.ACCENT}; border-radius: 2px; border: none;"
        )
        cl.addWidget(accent_bar)

        title = QLabel("Project for AI")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {Colors.TEXT_BRIGHT}; border: none;"
        )
        cl.addWidget(title)

        sub = QLabel("Classical AI Search & Pathfinding")
        sub.setStyleSheet(
            f"font-size: 12px; color: {Colors.TEXT_DIM}; border: none;"
        )
        cl.addWidget(sub)

        cl.addStretch()

        self.status_lbl = QLabel("Starting...")
        self.status_lbl.setStyleSheet(
            f"font-size: 11px; color: {Colors.TEXT_DIM}; border: none;"
        )
        cl.addWidget(self.status_lbl)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet(
            f"QProgressBar {{ background-color: {Colors.BORDER}; border-radius: 3px; border: none; }}"
            f"QProgressBar::chunk {{ background-color: {Colors.ACCENT}; border-radius: 3px; }}"
        )
        cl.addWidget(self.progress)

        outer.addWidget(card)

    def start(self):
        self.show()
        self._step_idx = 0
        self._advance()
        self._timer.start()

    def _advance(self):
        if self._step_idx >= len(self.STEPS):
            self._timer.stop()
            self.close()
            self.finished.emit()
            return

        pct, msg = self.STEPS[self._step_idx]
        self.progress.setValue(pct)
        self.status_lbl.setText(msg)
        self._step_idx += 1
