from __future__ import annotations
from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsRectItem, QGraphicsPathItem,
    QGraphicsSimpleTextItem,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QColor, QBrush, QPen, QPainterPath, QFont

from core.trace import EventKind, StepEvent
from problems.grid_problem import Coord, GridProblem
from ui.canvas.base_view import ZoomableGraphicsView
from ui.theme import Colors


class GridView(ZoomableGraphicsView):

    node_hovered = pyqtSignal(object, float, float, object)
    problem_modified = pyqtSignal()

    CELL_SIZE = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setViewportUpdateMode(ZoomableGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setMouseTracking(True)

        self._problem: GridProblem | None = None
        self._cells: dict[Coord, QGraphicsRectItem] = {}
        self._cost_labels: dict[Coord, QGraphicsSimpleTextItem] = {}
        self._path_item: QGraphicsPathItem | None = None

        self._cell_states: dict[Coord, str] = {}
        self._node_info: dict[Coord, tuple[float, float, Coord | None]] = {}
        self._show_costs: bool = False

        self._drag_mode: str | None = None
        self._paint_weight: float = 5.0

    def set_show_costs(self, enabled: bool):
        self._show_costs = enabled
        for pos, item in self._cost_labels.items():
            item.setVisible(enabled and pos in self._node_info)

    def set_problem(self, problem: GridProblem):
        self._problem = problem
        self._rebuild_scene()

    def _rebuild_scene(self):
        self._scene.clear()
        self._cells.clear()
        self._cost_labels.clear()
        self._cell_states.clear()
        self._node_info.clear()
        self._path_item = None

        if not self._problem:
            return

        s = self.CELL_SIZE
        cost_font = QFont("Cascadia Code", 7)
        border_pen = QPen(QColor(Colors.BORDER), 0.8)

        for r in range(self._problem.rows):
            for c in range(self._problem.cols):
                pos = (r, c)
                rect = self._scene.addRect(c * s, r * s, s, s, border_pen)
                rect.setZValue(1)
                self._cells[pos] = rect

                txt = self._scene.addSimpleText("", cost_font)
                txt.setBrush(QBrush(QColor(Colors.TEXT_BRIGHT)))
                txt.setPos(c * s + 2, r * s + 2)
                txt.setZValue(3)
                txt.setVisible(False)
                self._cost_labels[pos] = txt

                self._refresh_cell(pos)

        self._scene.setSceneRect(
            -4, -4, self._problem.cols * s + 8, self._problem.rows * s + 8
        )
        self.fit_scene(self._scene.sceneRect())

    def _refresh_cell(self, pos: Coord):
        if not self._problem or pos not in self._cells:
            return
        rect = self._cells[pos]

        if pos == self._problem.initial:
            color = QColor(Colors.START)
        elif pos in self._problem.goals:
            color = QColor(Colors.GOAL)
        elif pos in self._problem.walls:
            color = QColor(Colors.WALL)
        elif pos in self._cell_states:
            st = self._cell_states[pos]
            if st == "PATH":
                color = QColor(Colors.PATH)
            elif st == "VISITED":
                color = QColor(Colors.VISITED)
            elif st == "FRONTIER":
                color = QColor(Colors.FRONTIER)
            elif st == "PRUNED":
                color = QColor(Colors.PRUNED)
            else:
                color = QColor(Colors.BG_SURFACE)
        elif pos in self._problem.weights and self._problem.weights[pos] > 1.0:
            w = min(self._problem.weights[pos], 10.0)
            ratio = (w - 1.0) / 9.0
            low = QColor(Colors.WEIGHT_LOW)
            high = QColor(Colors.WEIGHT_HIGH)
            r = int(low.red() + ratio * (high.red() - low.red()))
            g = int(low.green() + ratio * (high.green() - low.green()))
            b = int(low.blue() + ratio * (high.blue() - low.blue()))
            color = QColor(r, g, b)
        else:
            color = QColor(Colors.BG_SURFACE)

        rect.setBrush(QBrush(color))

    def refresh_theme(self):
        super().refresh_theme()
        border_pen = QPen(QColor(Colors.BORDER), 0.8)
        for pos, rect in self._cells.items():
            rect.setPen(border_pen)
            self._refresh_cell(pos)
        for txt in self._cost_labels.values():
            txt.setBrush(QBrush(QColor(Colors.TEXT_BRIGHT)))

    def clear_search(self):
        self._cell_states.clear()
        self._node_info.clear()
        if self._path_item is not None:
            self._scene.removeItem(self._path_item)
            self._path_item = None
        for pos, txt in self._cost_labels.items():
            txt.setText("")
            txt.setVisible(False)
        for pos in self._cells:
            self._refresh_cell(pos)

    def apply_event(self, event: StepEvent):
        pos = event.state
        if not isinstance(pos, tuple) or pos not in self._cells:
            return

        self._node_info[pos] = (event.g, event.h, event.parent_state)
        if pos in self._cost_labels:
            lbl = self._cost_labels[pos]
            lbl.setText(f"{event.f:.0f}")
            lbl.setVisible(self._show_costs)

        if event.kind == EventKind.EXPAND:
            self._cell_states[pos] = "VISITED"
        elif event.kind in (EventKind.GENERATE, EventKind.UPDATE):
            if self._cell_states.get(pos) != "VISITED":
                self._cell_states[pos] = "FRONTIER"
        elif event.kind == EventKind.PRUNE:
            self._cell_states[pos] = "PRUNED"
        elif event.kind == EventKind.GOAL_FOUND:
            self._cell_states[pos] = "PATH"

        self._refresh_cell(pos)

    def set_path(self, path: list[Coord]):
        if self._path_item is not None:
            self._scene.removeItem(self._path_item)
            self._path_item = None

        if not path or len(path) < 2:
            return

        s = self.CELL_SIZE
        qpath = QPainterPath()
        r0, c0 = path[0]
        qpath.moveTo(c0 * s + s / 2, r0 * s + s / 2)
        for pos in path[1:]:
            r, c = pos
            qpath.lineTo(c * s + s / 2, r * s + s / 2)
            if pos != self._problem.initial and pos not in self._problem.goals:
                self._cell_states[pos] = "PATH"
                self._refresh_cell(pos)

        pen = QPen(QColor("#ffffff"), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self._path_item = self._scene.addPath(qpath, pen)
        self._path_item.setZValue(4)

    def _cell_at_viewport_pos(self, pos) -> Coord | None:
        if not self._problem:
            return None
        scene_pt: QPointF = self.mapToScene(pos)
        c = int(scene_pt.x() // self.CELL_SIZE)
        r = int(scene_pt.y() // self.CELL_SIZE)
        coord = (r, c)
        return coord if self._problem.in_bounds(coord) else None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton
            and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            super().mousePressEvent(event)
            return
        if not self._problem:
            return
        coord = self._cell_at_viewport_pos(event.pos())
        if coord is None:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if coord == self._problem.initial:
                self._drag_mode = "move_start"
            elif coord in self._problem.goals:
                self._drag_mode = "move_goal"
                self._moving_goal = coord
            elif event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._drag_mode = "add_weight" if coord not in self._problem.weights else "remove_weight"
                self._apply_drag_paint(coord)
            else:
                self._drag_mode = "erase_wall" if coord in self._problem.walls else "draw_wall"
                self._apply_drag_paint(coord)

    def mouseMoveEvent(self, event):
        if self._panning:
            super().mouseMoveEvent(event)
            return
        coord = self._cell_at_viewport_pos(event.pos())
        if coord is not None and self._problem is not None:
            g, h, parent = self._node_info.get(coord, (0.0, self._problem.heuristic(coord), None))
            self.node_hovered.emit(coord, g, h, parent)

        if self._drag_mode and coord is not None:
            self._apply_drag_paint(coord)

    def mouseReleaseEvent(self, event):
        if self._panning:
            super().mouseReleaseEvent(event)
            return
        if self._drag_mode:
            self._drag_mode = None
            self.problem_modified.emit()

    def _apply_drag_paint(self, coord: Coord):
        if not self._problem:
            return
        if self._drag_mode == "move_start":
            if coord not in self._problem.walls and coord not in self._problem.goals:
                old = self._problem.initial
                self._problem.initial = coord
                self._refresh_cell(old)
                self._refresh_cell(coord)
        elif self._drag_mode == "move_goal":
            if coord not in self._problem.walls and coord != self._problem.initial:
                old = getattr(self, "_moving_goal", None)
                if old in self._problem._goal:
                    self._problem._goal.discard(old)
                    self._refresh_cell(old)
                self._problem._goal.add(coord)
                self._moving_goal = coord
                self._refresh_cell(coord)
        elif self._drag_mode == "draw_wall":
            if coord != self._problem.initial and coord not in self._problem.goals:
                self._problem.walls.add(coord)
                self._problem.weights.pop(coord, None)
                self._refresh_cell(coord)
        elif self._drag_mode == "erase_wall":
            self._problem.walls.discard(coord)
            self._refresh_cell(coord)
        elif self._drag_mode == "add_weight":
            if coord != self._problem.initial and coord not in self._problem.goals:
                self._problem.walls.discard(coord)
                self._problem.weights[coord] = self._paint_weight
                self._refresh_cell(coord)
        elif self._drag_mode == "remove_weight":
            self._problem.weights.pop(coord, None)
            self._refresh_cell(coord)
