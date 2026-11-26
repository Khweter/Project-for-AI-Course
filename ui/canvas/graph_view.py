from __future__ import annotations
import math
from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem,
    QGraphicsPolygonItem, QGraphicsSimpleTextItem, QGraphicsItem,
    QInputDialog, QMenu, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QCheckBox, QPushButton, QScrollArea,
    QWidget, QComboBox, QLabel, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QColor, QBrush, QPen, QFont, QPolygonF

from core.trace import EventKind, StepEvent
from problems.graph_problem import GraphProblem
from ui.canvas.base_view import ZoomableGraphicsView
from ui.theme import Colors, build_stylesheet
from ui.widgets.spinbox import CleanDoubleSpinBox


def _prompt_double(
    parent: QWidget,
    title: str,
    label: str,
    value: float,
    min_val: float = 0.0,
    max_val: float = 100000.0,
    decimals: int = 1,
) -> tuple[float, bool]:
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumWidth(260)
    dlg.setStyleSheet(build_stylesheet())

    layout = QVBoxLayout(dlg)
    layout.addWidget(QLabel(label))

    spin = CleanDoubleSpinBox()
    spin.setRange(min_val, max_val)
    spin.setDecimals(decimals)
    spin.setValue(value)
    spin.selectAll()
    layout.addWidget(spin)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    layout.addWidget(buttons)

    ok = dlg.exec() == QDialog.DialogCode.Accepted
    return spin.value(), ok


class AddNodeDialog(QDialog):

    def __init__(self, existing_nodes: list[str], suggested_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Node & Connect")
        self.setMinimumWidth(360)
        self.setStyleSheet(build_stylesheet())

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        self.name_edit = QLineEdit(suggested_name)
        form.addRow("Node Name:", self.name_edit)

        self.chk_custom_h = QCheckBox("Set custom heuristic h(n)")
        self.h_spin = CleanDoubleSpinBox()
        self.h_spin.setRange(0.0, 100000.0)
        self.h_spin.setDecimals(1)
        self.h_spin.setEnabled(False)
        self.chk_custom_h.toggled.connect(self.h_spin.setEnabled)
        form.addRow(self.chk_custom_h, self.h_spin)
        layout.addLayout(form)

        self._connections: dict[str, tuple[QCheckBox, CleanDoubleSpinBox]] = {}
        if existing_nodes:
            lbl = QLabel("Connect to existing nodes (with edge cost):")
            lbl.setObjectName("dim")
            layout.addWidget(lbl)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(220)
            container = QWidget()
            cl = QVBoxLayout(container)
            cl.setSpacing(6)

            for node in existing_nodes:
                row = QHBoxLayout()
                cb = QCheckBox(node)
                spin = CleanDoubleSpinBox()
                spin.setRange(0.1, 100000.0)
                spin.setDecimals(1)
                spin.setValue(10.0)
                spin.setEnabled(False)
                cb.toggled.connect(spin.setEnabled)
                row.addWidget(cb, stretch=1)
                row.addWidget(spin)
                cl.addLayout(row)
                self._connections[node] = (cb, spin)
            cl.addStretch()
            scroll.setWidget(container)
            layout.addWidget(scroll)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def node_name(self) -> str:
        return self.name_edit.text().strip()

    def custom_heuristic(self) -> float | None:
        return self.h_spin.value() if self.chk_custom_h.isChecked() else None

    def selected_edges(self) -> list[tuple[str, float]]:
        return [
            (name, spin.value())
            for name, (cb, spin) in self._connections.items()
            if cb.isChecked()
        ]


class ConnectEdgeDialog(QDialog):

    def __init__(
        self,
        nodes: list[str],
        source: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Connect Nodes")
        self.setMinimumWidth(300)
        self.setStyleSheet(build_stylesheet())

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.src_combo = QComboBox()
        self.src_combo.addItems(nodes)
        if source and source in nodes:
            self.src_combo.setCurrentText(source)
            self.src_combo.setEnabled(False)
        form.addRow("From:", self.src_combo)

        self.dst_combo = QComboBox()
        targets = [n for n in nodes if n != source] if source else list(nodes)
        self.dst_combo.addItems(targets)
        form.addRow("To:", self.dst_combo)

        self.weight_spin = CleanDoubleSpinBox()
        self.weight_spin.setRange(0.1, 100000.0)
        self.weight_spin.setDecimals(1)
        self.weight_spin.setValue(10.0)
        form.addRow("Cost:", self.weight_spin)

        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_edge(self) -> tuple[str, str, float]:
        return (
            self.src_combo.currentText(),
            self.dst_combo.currentText(),
            self.weight_spin.value(),
        )


class GraphNodeItem(QGraphicsEllipseItem):

    RADIUS = 18

    def __init__(self, name: str, view: GraphView):
        r = self.RADIUS
        super().__init__(-r, -r, r * 2, r * 2)
        self.name = name
        self._view = view
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setZValue(5)

        self._label = QGraphicsSimpleTextItem(name, self)
        self._label.setBrush(QBrush(QColor(Colors.TEXT_BRIGHT)))
        self._label.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        br = self._label.boundingRect()
        self._label.setPos(-br.width() / 2, r + 3)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._view._on_node_moved(self.name, value)
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        self._view._on_node_hovered(self.name)
        super().hoverEnterEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self._view._handle_edge_click(self.name)
            event.accept()
            return
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class GraphView(ZoomableGraphicsView):

    node_hovered = pyqtSignal(object, float, float, object)
    problem_modified = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setViewportUpdateMode(ZoomableGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        self._problem: GraphProblem | None = None
        self._node_items: dict[str, GraphNodeItem] = {}
        self._edge_items: dict[tuple[str, str], tuple[QGraphicsLineItem, QGraphicsSimpleTextItem, QGraphicsPolygonItem | None]] = {}

        self._node_states: dict[str, str] = {}
        self._edge_states: dict[tuple[str, str], str] = {}
        self._node_info: dict[str, tuple[float, float, str | None]] = {}
        self._edge_source: str | None = None

    def set_problem(self, problem: GraphProblem):
        self._problem = problem
        self._edge_source = None
        self._rebuild_scene()

    def _rebuild_scene(self):
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._node_states.clear()
        self._edge_states.clear()
        self._node_info.clear()

        if not self._problem:
            return

        for u, v, w in self._problem.edge_list():
            self._create_edge_graphics(u, v, w)

        for name, (x, y) in self._problem.nodes.items():
            item = GraphNodeItem(name, self)
            item.setPos(x, y)
            self._scene.addItem(item)
            self._node_items[name] = item
            self._refresh_node(name)

        self._fit_bounds()

    def _fit_bounds(self):
        if not self._problem or not self._problem.nodes:
            return
        rect = self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
        self._scene.setSceneRect(rect)
        self.fit_scene(rect)

    def _create_edge_graphics(self, u: str, v: str, weight: float):
        line = QGraphicsLineItem()
        line.setZValue(1)
        self._scene.addItem(line)

        label = QGraphicsSimpleTextItem(f"{weight:g}")
        label.setFont(QFont("Cascadia Code", 8))
        label.setBrush(QBrush(QColor(Colors.TEXT_DIM)))
        label.setZValue(3)
        self._scene.addItem(label)

        arrow = None
        if self._problem and self._problem.directed:
            arrow = QGraphicsPolygonItem()
            arrow.setZValue(2)
            self._scene.addItem(arrow)

        self._edge_items[(u, v)] = (line, label, arrow)
        self._update_edge_geometry(u, v)
        self._refresh_edge((u, v))

    def _update_edge_geometry(self, u: str, v: str):
        if not self._problem or (u, v) not in self._edge_items:
            return
        x1, y1 = self._problem.nodes.get(u, (0.0, 0.0))
        x2, y2 = self._problem.nodes.get(v, (0.0, 0.0))
        line, label, arrow = self._edge_items[(u, v)]
        line.setLine(x1, y1, x2, y2)

        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length
        br = label.boundingRect()
        label.setPos(mx + nx * 10 - br.width() / 2, my + ny * 10 - br.height() / 2)

        if arrow is not None:
            ux, uy = dx / length, dy / length
            tip_x = x2 - ux * GraphNodeItem.RADIUS
            tip_y = y2 - uy * GraphNodeItem.RADIUS
            sz = 8.0
            p1 = QPointF(tip_x, tip_y)
            p2 = QPointF(tip_x - ux * sz + nx * sz * 0.5, tip_y - uy * sz + ny * sz * 0.5)
            p3 = QPointF(tip_x - ux * sz - nx * sz * 0.5, tip_y - uy * sz - ny * sz * 0.5)
            arrow.setPolygon(QPolygonF([p1, p2, p3]))

    def _edge_key(self, u: str, v: str) -> tuple[str, str]:
        if (u, v) in self._edge_items:
            return (u, v)
        return (v, u)

    def _edge_at_scene_pos(self, pt: QPointF, max_dist: float = 10.0) -> tuple[str, str] | None:
        if not self._problem:
            return None
        for (u, v), (line, label, _) in self._edge_items.items():
            if label.contains(label.mapFromScene(pt)):
                return (u, v)
            x1, y1 = self._problem.nodes.get(u, (0.0, 0.0))
            x2, y2 = self._problem.nodes.get(v, (0.0, 0.0))
            dx, dy = x2 - x1, y2 - y1
            len_sq = dx * dx + dy * dy
            if len_sq == 0:
                continue
            t = max(0.0, min(1.0, ((pt.x() - x1) * dx + (pt.y() - y1) * dy) / len_sq))
            proj_x, proj_y = x1 + t * dx, y1 + t * dy
            if math.hypot(pt.x() - proj_x, pt.y() - proj_y) <= max_dist:
                return (u, v)
        return None

    def _refresh_node(self, name: str):
        if not self._problem or name not in self._node_items:
            return
        item = self._node_items[name]
        state = self._node_states.get(name)

        if name == self._problem.initial:
            fill = QColor(Colors.START)
            border = QColor(Colors.TEXT_BRIGHT)
        elif name in self._problem.goals:
            fill = QColor(Colors.GOAL)
            border = QColor(Colors.TEXT_BRIGHT)
        elif state == "PATH":
            fill = QColor(Colors.PATH)
            border = QColor(Colors.TEXT_BRIGHT)
        elif state == "VISITED":
            fill = QColor(Colors.VISITED)
            border = QColor(Colors.ACCENT)
        elif state == "FRONTIER":
            fill = QColor(Colors.FRONTIER)
            border = QColor(Colors.TEXT_BRIGHT)
        elif state == "PRUNED":
            fill = QColor(Colors.PRUNED)
            border = QColor(Colors.ERROR)
        else:
            fill = QColor(Colors.BG_ELEVATED)
            border = QColor(Colors.BORDER_LIGHT)

        if self._edge_source == name:
            border = QColor(Colors.ACCENT_HOVER)

        item.setBrush(QBrush(fill))
        item.setPen(QPen(border, 2.2))

    def _refresh_edge(self, key: tuple[str, str]):
        if key not in self._edge_items:
            return
        line, label, arrow = self._edge_items[key]
        state = self._edge_states.get(key)
        if state == "PATH":
            color = QColor(Colors.PATH)
            width = 3.5
            label.setBrush(QBrush(QColor(Colors.TEXT_BRIGHT)))
        elif state == "TRAVERSED":
            color = QColor(Colors.ACCENT_DIM)
            width = 2.2
            label.setBrush(QBrush(QColor(Colors.TEXT)))
        else:
            color = QColor(Colors.BORDER_LIGHT)
            width = 1.5
            label.setBrush(QBrush(QColor(Colors.TEXT_DIM)))

        line.setPen(QPen(color, width))
        if arrow is not None:
            arrow.setBrush(QBrush(color))
            arrow.setPen(QPen(color, 1))

    def refresh_theme(self):
        super().refresh_theme()
        for name, item in self._node_items.items():
            item._label.setBrush(QBrush(QColor(Colors.TEXT_BRIGHT)))
            self._refresh_node(name)
        for key in self._edge_items:
            self._refresh_edge(key)

    def clear_search(self):
        self._node_states.clear()
        self._edge_states.clear()
        self._node_info.clear()
        for name in self._node_items:
            self._refresh_node(name)
        for key in self._edge_items:
            self._refresh_edge(key)

    def apply_event(self, event: StepEvent):
        name = str(event.state)
        if name not in self._node_items:
            return

        self._node_info[name] = (event.g, event.h, event.parent_state)

        if event.parent_state is not None:
            ekey = self._edge_key(str(event.parent_state), name)
            if ekey in self._edge_items and self._edge_states.get(ekey) != "PATH":
                self._edge_states[ekey] = "TRAVERSED"
                self._refresh_edge(ekey)

        if event.kind == EventKind.EXPAND:
            self._node_states[name] = "VISITED"
        elif event.kind in (EventKind.GENERATE, EventKind.UPDATE):
            if self._node_states.get(name) != "VISITED":
                self._node_states[name] = "FRONTIER"
        elif event.kind == EventKind.PRUNE:
            self._node_states[name] = "PRUNED"
        elif event.kind == EventKind.GOAL_FOUND:
            self._node_states[name] = "PATH"

        self._refresh_node(name)

    def set_path(self, path: list[str]):
        if not path:
            return
        for name in path:
            self._node_states[name] = "PATH"
            self._refresh_node(name)
        for i in range(len(path) - 1):
            ekey = self._edge_key(path[i], path[i + 1])
            if ekey in self._edge_items:
                self._edge_states[ekey] = "PATH"
                self._refresh_edge(ekey)

    def _on_node_moved(self, name: str, pos: QPointF):
        if not self._problem:
            return
        self._problem.nodes[name] = (pos.x(), pos.y())
        for u, v in list(self._edge_items.keys()):
            if u == name or v == name:
                self._update_edge_geometry(u, v)

    def _on_node_hovered(self, name: str):
        if not self._problem:
            return
        g, h, parent = self._node_info.get(name, (0.0, self._problem.heuristic(name), None))
        self.node_hovered.emit(name, g, h, parent)

    def _handle_edge_click(self, name: str):
        if not self._problem:
            return
        if self._edge_source is None:
            self._edge_source = name
            self._refresh_node(name)
            return

        src = self._edge_source
        self._edge_source = None
        self._refresh_node(src)
        if src == name:
            return

        current_w = self._problem.adj.get(src, {}).get(name, 10.0)
        weight, ok = _prompt_double(
            self, "Edge Cost", f"Cost for {src} -> {name}:", current_w, 0.1, 100000.0, 1
        )
        if ok:
            self._problem.add_edge(src, name, weight)
            self._rebuild_scene()
            self.problem_modified.emit()

    def _edit_edge_weight(self, u: str, v: str):
        if not self._problem:
            return
        current_w = self._problem.adj.get(u, {}).get(v, 10.0)
        weight, ok = _prompt_double(
            self, "Edit Edge Cost", f"Cost for {u} -> {v}:", current_w, 0.1, 100000.0, 1
        )
        if ok:
            self._problem.add_edge(u, v, weight)
            self._rebuild_scene()
            self.problem_modified.emit()

    def prompt_add_node(self, pos: QPointF | None = None):
        if not self._problem:
            return
        idx = len(self._problem.nodes) + 1
        suggested = f"N{idx}"
        while suggested in self._problem.nodes:
            idx += 1
            suggested = f"N{idx}"

        existing = sorted(self._problem.nodes.keys())
        dlg = AddNodeDialog(existing, suggested, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name = dlg.node_name()
        if not name or name in self._problem.nodes:
            return

        if pos is None:
            center = self._scene.sceneRect().center() if not self._scene.sceneRect().isNull() else QPointF(200, 200)
            pos = center
        self._problem.add_node(name, (pos.x(), pos.y()))
        h_val = dlg.custom_heuristic()
        if h_val is not None:
            self._problem.custom_heuristics[name] = h_val
        for target, cost in dlg.selected_edges():
            self._problem.add_edge(name, target, cost)

        self._rebuild_scene()
        self.problem_modified.emit()

    def prompt_add_edge(self, source: str | None = None):
        if not self._problem or len(self._problem.nodes) < 2:
            return
        dlg = ConnectEdgeDialog(sorted(self._problem.nodes.keys()), source=source, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        u, v, w = dlg.result_edge()
        if u and v and u != v:
            self._problem.add_edge(u, v, w)
            self._rebuild_scene()
            self.problem_modified.emit()

    def mouseDoubleClickEvent(self, event):
        if not self._problem:
            return
        scene_pt = self.mapToScene(event.pos())
        for item in self._scene.items(scene_pt):
            if isinstance(item, GraphNodeItem):
                return
        edge = self._edge_at_scene_pos(scene_pt)
        if edge:
            self._edit_edge_weight(*edge)
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        if not self._problem:
            return
        scene_pt = self.mapToScene(event.pos())
        clicked_node = None
        for item in self._scene.items(scene_pt):
            if isinstance(item, GraphNodeItem):
                clicked_node = item.name
                break

        menu = QMenu(self)
        if clicked_node:
            act_connect = menu.addAction(f"Connect '{clicked_node}' To...")
            act_rename = menu.addAction(f"Rename '{clicked_node}'...")
            act_heur = menu.addAction(f"Set Heuristic h('{clicked_node}')...")
            menu.addSeparator()
            act_start = menu.addAction(f"Set '{clicked_node}' as Start")
            act_goal = menu.addAction(f"Set '{clicked_node}' as Goal")
            act_del = menu.addAction(f"Delete '{clicked_node}'")
            chosen = menu.exec(event.globalPos())

            if chosen == act_connect:
                self.prompt_add_edge(source=clicked_node)
            elif chosen == act_rename:
                new_name, ok = QInputDialog.getText(
                    self, "Rename Node", "New name:", text=clicked_node
                )
                if ok and new_name.strip() and new_name.strip() not in self._problem.nodes:
                    self._problem.rename_node(clicked_node, new_name.strip())
                    self._rebuild_scene()
                    self.problem_modified.emit()
            elif chosen == act_heur:
                cur_h = self._problem.heuristic(clicked_node)
                val, ok = _prompt_double(
                    self, "Node Heuristic", f"h({clicked_node}):", cur_h, 0.0, 100000.0, 1
                )
                if ok:
                    self._problem.custom_heuristics[clicked_node] = val
                    self.problem_modified.emit()
            elif chosen == act_start:
                self._problem.initial = clicked_node
                self._rebuild_scene()
                self.problem_modified.emit()
            elif chosen == act_goal:
                self._problem._goal = {clicked_node}
                self._rebuild_scene()
                self.problem_modified.emit()
            elif chosen == act_del and clicked_node != self._problem.initial:
                self._problem.remove_node(clicked_node)
                self._rebuild_scene()
                self.problem_modified.emit()
            return

        edge = self._edge_at_scene_pos(scene_pt)
        if edge:
            u, v = edge
            act_edit = menu.addAction(f"Edit Cost ({u} -> {v})...")
            act_del = menu.addAction(f"Delete Edge ({u} -> {v})")
            chosen = menu.exec(event.globalPos())
            if chosen == act_edit:
                self._edit_edge_weight(u, v)
            elif chosen == act_del:
                self._problem.remove_edge(u, v)
                self._rebuild_scene()
                self.problem_modified.emit()
            return

        act_add_node = menu.addAction("Add Node Here...")
        act_add_edge = menu.addAction("Connect Nodes...")
        chosen = menu.exec(event.globalPos())
        if chosen == act_add_node:
            self.prompt_add_node(scene_pt)
        elif chosen == act_add_edge:
            self.prompt_add_edge()
