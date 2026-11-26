from __future__ import annotations
from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsRectItem, QGraphicsSimpleTextItem,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QBrush, QPen, QFont

from core.trace import EventKind, StepEvent
from problems.puzzle_problem import Board, PuzzleProblem
from ui.canvas.base_view import ZoomableGraphicsView
from ui.theme import Colors


class PuzzleView(ZoomableGraphicsView):

    node_hovered = pyqtSignal(object, float, float, object)
    problem_modified = pyqtSignal()

    TILE_SIZE = 96
    GAP = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._problem: PuzzleProblem | None = None
        self._current_board: Board | None = None
        self._tiles: dict[int, QGraphicsRectItem] = {}
        self._anims: list[QVariantAnimation] = []
        self._solved_highlight: bool = False

    def set_problem(self, problem: PuzzleProblem):
        self._problem = problem
        self._solved_highlight = False
        self._rebuild_scene()

    def _tile_pos(self, idx: int) -> QPointF:
        r, c = divmod(idx, 3)
        step = self.TILE_SIZE + self.GAP
        return QPointF(c * step, r * step)

    def _rebuild_scene(self):
        self._stop_anims()
        self._scene.clear()
        self._tiles.clear()

        if not self._problem:
            return

        total = 3 * self.TILE_SIZE + 2 * self.GAP
        pad = 14
        board_bg = self._scene.addRect(
            -pad, -pad, total + 2 * pad, total + 2 * pad,
            QPen(QColor(Colors.BORDER_LIGHT), 1.5),
            QBrush(QColor(Colors.BG_SECONDARY)),
        )
        board_bg.setZValue(0)
        self._board_bg = board_bg
        self._slots: list[QGraphicsRectItem] = []
        self._tile_labels: list[QGraphicsSimpleTextItem] = []

        for idx in range(9):
            pt = self._tile_pos(idx)
            slot = self._scene.addRect(
                pt.x(), pt.y(), self.TILE_SIZE, self.TILE_SIZE,
                QPen(QColor(Colors.BORDER), 1.0),
                QBrush(QColor(Colors.BG_PRIMARY)),
            )
            slot.setZValue(1)
            self._slots.append(slot)

        font = QFont("Cascadia Code", 26, QFont.Weight.Bold)
        self._current_board = self._problem.initial

        for idx, tile in enumerate(self._current_board):
            if tile == 0:
                continue
            rect = QGraphicsRectItem(0, 0, self.TILE_SIZE, self.TILE_SIZE)
            rect.setPos(self._tile_pos(idx))
            rect.setZValue(2)
            self._scene.addItem(rect)

            lbl = QGraphicsSimpleTextItem(str(tile), rect)
            lbl.setFont(font)
            lbl.setBrush(QBrush(QColor(Colors.TEXT_BRIGHT)))
            br = lbl.boundingRect()
            lbl.setPos(
                (self.TILE_SIZE - br.width()) / 2,
                (self.TILE_SIZE - br.height()) / 2,
            )
            self._tile_labels.append(lbl)
            self._tiles[tile] = rect

        self._refresh_tile_colors()
        self._scene.setSceneRect(-pad - 10, -pad - 10, total + 2 * pad + 20, total + 2 * pad + 20)
        self.fit_scene(self._scene.sceneRect())

    def _stop_anims(self):
        for anim in self._anims:
            anim.stop()
        self._anims.clear()

    def _refresh_tile_colors(self):
        if not self._problem or not self._current_board:
            return
        for idx, tile in enumerate(self._current_board):
            if tile == 0 or tile not in self._tiles:
                continue
            rect = self._tiles[tile]
            in_goal_spot = self._problem.goal_board[idx] == tile
            if self._solved_highlight:
                fill = QColor(Colors.ACCENT_DIM)
                border = QColor(Colors.ACCENT)
            elif in_goal_spot:
                fill = QColor(Colors.VISITED)
                border = QColor(Colors.ACCENT_DIM)
            else:
                fill = QColor(Colors.BG_ELEVATED)
                border = QColor(Colors.BORDER_LIGHT)
            rect.setBrush(QBrush(fill))
            rect.setPen(QPen(border, 2.0))

    def _display_board(self, board: Board, animate: bool = True):
        if not self._current_board or board == self._current_board:
            return
        self._stop_anims()
        self._current_board = board

        for idx, tile in enumerate(board):
            if tile == 0 or tile not in self._tiles:
                continue
            rect = self._tiles[tile]
            target = self._tile_pos(idx)
            if animate and rect.pos() != target:
                start_pos = rect.pos()
                anim = QVariantAnimation(self)
                anim.setDuration(90)
                anim.setStartValue(start_pos)
                anim.setEndValue(target)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.valueChanged.connect(lambda val, r=rect: r.setPos(val))
                anim.start()
                self._anims.append(anim)
            else:
                rect.setPos(target)

        self._refresh_tile_colors()

    def refresh_theme(self):
        super().refresh_theme()
        if hasattr(self, "_board_bg") and self._board_bg:
            self._board_bg.setPen(QPen(QColor(Colors.BORDER_LIGHT), 1.5))
            self._board_bg.setBrush(QBrush(QColor(Colors.BG_SECONDARY)))
        for slot in getattr(self, "_slots", []):
            slot.setPen(QPen(QColor(Colors.BORDER), 1.0))
            slot.setBrush(QBrush(QColor(Colors.BG_PRIMARY)))
        for lbl in getattr(self, "_tile_labels", []):
            lbl.setBrush(QBrush(QColor(Colors.TEXT_BRIGHT)))
        self._refresh_tile_colors()

    def clear_search(self):
        self._solved_highlight = False
        if self._problem:
            self._display_board(self._problem.initial, animate=False)
            self._refresh_tile_colors()

    def apply_event(self, event: StepEvent):
        if not isinstance(event.state, tuple) or len(event.state) != 9:
            return
        if event.kind in (EventKind.EXPAND, EventKind.GOAL_FOUND):
            self._solved_highlight = event.kind == EventKind.GOAL_FOUND
            self._display_board(event.state, animate=True)
            self.node_hovered.emit(event.state, event.g, event.h, event.parent_state)

    def set_path(self, path: list[Board]):
        if not path:
            return
        self._solved_highlight = True
        self._display_board(path[-1], animate=True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton
            and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            super().mousePressEvent(event)
            return
        if not self._problem or event.button() != Qt.MouseButton.LeftButton:
            return
        scene_pt = self.mapToScene(event.pos())
        step = self.TILE_SIZE + self.GAP
        c = int(scene_pt.x() // step)
        r = int(scene_pt.y() // step)
        if not (0 <= r < 3 and 0 <= c < 3):
            return

        clicked_idx = r * 3 + c
        board = list(self._problem.initial)
        blank_idx = board.index(0)
        br, bc = divmod(blank_idx, 3)
        if abs(br - r) + abs(bc - c) == 1:
            board[blank_idx], board[clicked_idx] = board[clicked_idx], board[blank_idx]
            new_board = tuple(board)
            self._problem.initial = new_board
            self._display_board(new_board, animate=True)
            self.node_hovered.emit(new_board, 0.0, self._problem.heuristic(new_board), None)
            self.problem_modified.emit()
