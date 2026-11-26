from __future__ import annotations
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
    QPushButton, QFormLayout, QWidget, QCheckBox,
)
from PyQt6.QtCore import pyqtSignal

import algorithms
from presets.scenarios import preset_names
from ui.playback import IconButton
from ui.theme import Colors, current_theme, SPACING
from ui.widgets.spinbox import CleanSpinBox


class ControlPanel(QFrame):

    problem_changed = pyqtSignal(str)
    preset_changed = pyqtSignal(str)
    algorithm_changed = pyqtSignal(str)
    run_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    reset_requested = pyqtSignal()
    maze_requested = pyqtSignal(str)
    clear_walls_requested = pyqtSignal()
    show_costs_toggled = pyqtSignal(bool)
    diagonal_toggled = pyqtSignal(bool)
    compare_requested = pyqtSignal()
    save_requested = pyqtSignal()
    add_node_requested = pyqtSignal()
    add_edge_requested = pyqtSignal()
    directed_toggled = pyqtSignal(bool)
    theme_toggled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._build_ui()
        self._sync_problem_controls(self.problem_combo.currentText())
        self._sync_algo_controls(self.algo_combo.currentText())

    def _make_card(self, title: str) -> tuple[QFrame, QFormLayout]:
        card = QFrame()
        card.setObjectName("card")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(12, 10, 12, 12)
        outer.setSpacing(8)

        hdr = QLabel(title)
        hdr.setObjectName("section-title")
        outer.addWidget(hdr)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        outer.addLayout(form)
        return card, form

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        brand = QWidget()
        bl = QVBoxLayout(brand)
        bl.setContentsMargins(2, 0, 2, 4)
        bl.setSpacing(2)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        self.title_lbl = QLabel("Project for AI")
        self.title_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_BRIGHT};"
        )
        top_row.addWidget(self.title_lbl)
        top_row.addStretch()

        self.theme_btn = IconButton("moon" if current_theme() == "light" else "sun", size=30)
        self.theme_btn.setToolTip("Toggle Light / Dark Mode")
        self.theme_btn.clicked.connect(self.theme_toggled)
        top_row.addWidget(self.theme_btn)
        bl.addLayout(top_row)

        subtitle = QLabel("Classical AI Search & Pathfinding")
        subtitle.setObjectName("dim")
        bl.addWidget(subtitle)
        layout.addWidget(brand)

        problem_card, pf = self._make_card("Problem")
        self.problem_combo = QComboBox()
        self.problem_combo.addItems(["Grid Pathfinding", "Graph Search", "8-Puzzle"])
        self.problem_combo.currentTextChanged.connect(self._on_problem_changed)
        pf.addRow("Type", self.problem_combo)

        self.preset_combo = QComboBox()
        self.preset_combo.currentTextChanged.connect(self.preset_changed)
        pf.addRow("Preset", self.preset_combo)
        layout.addWidget(problem_card)

        algo_card, af = self._make_card("Algorithm")
        self.algo_combo = QComboBox()
        for info in algorithms.all_algorithms():
            self.algo_combo.addItem(info.name)
        self.algo_combo.currentTextChanged.connect(self._on_algo_changed)
        af.addRow("Search", self.algo_combo)

        self.category_badge = QLabel("Uninformed")
        self.category_badge.setObjectName("mono-badge")
        af.addRow("Class", self.category_badge)

        self.heuristic_label = QLabel("Heuristic")
        self.heuristic_combo = QComboBox()
        self.heuristic_combo.addItems(["Manhattan", "Euclidean", "Misplaced Tiles"])
        af.addRow(self.heuristic_label, self.heuristic_combo)
        layout.addWidget(algo_card)

        self.param_card, paf = self._make_card("Parameters")
        self.depth_label = QLabel("Depth Limit")
        self.depth_limit_spin = CleanSpinBox()
        self.depth_limit_spin.setRange(1, 1000)
        self.depth_limit_spin.setValue(50)
        paf.addRow(self.depth_label, self.depth_limit_spin)

        self.beam_label = QLabel("Beam Width")
        self.beam_width_spin = CleanSpinBox()
        self.beam_width_spin.setRange(1, 500)
        self.beam_width_spin.setValue(3)
        paf.addRow(self.beam_label, self.beam_width_spin)
        layout.addWidget(self.param_card)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.run_btn = QPushButton("Run Search")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run_requested)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_requested)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_requested)
        self.cancel_btn.setVisible(False)

        actions.addWidget(self.run_btn, stretch=1)
        actions.addWidget(self.reset_btn)
        actions.addWidget(self.cancel_btn)
        layout.addLayout(actions)

        bench_row = QHBoxLayout()
        bench_row.setSpacing(8)
        self.compare_btn = QPushButton("Compare All")
        self.compare_btn.clicked.connect(self.compare_requested)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_requested)
        bench_row.addWidget(self.compare_btn, stretch=1)
        bench_row.addWidget(self.save_btn)
        layout.addLayout(bench_row)

        self.grid_card = QFrame()
        self.grid_card.setObjectName("card")
        gl = QVBoxLayout(self.grid_card)
        gl.setContentsMargins(12, 10, 12, 12)
        gl.setSpacing(8)

        grid_hdr = QLabel("GRID TOOLS")
        grid_hdr.setObjectName("section-title")
        gl.addWidget(grid_hdr)

        maze_row = QHBoxLayout()
        maze_row.setSpacing(6)
        btn_bt = QPushButton("Backtracker")
        btn_bt.clicked.connect(lambda: self.maze_requested.emit("backtracker"))
        btn_pr = QPushButton("Prim's")
        btn_pr.clicked.connect(lambda: self.maze_requested.emit("prims"))
        btn_cw = QPushButton("Clear")
        btn_cw.clicked.connect(self.clear_walls_requested)
        maze_row.addWidget(btn_bt)
        maze_row.addWidget(btn_pr)
        maze_row.addWidget(btn_cw)
        gl.addLayout(maze_row)

        self.chk_costs = QCheckBox("Show f(n) overlay")
        self.chk_costs.toggled.connect(self.show_costs_toggled)
        gl.addWidget(self.chk_costs)

        self.chk_diag = QCheckBox("Allow diagonal moves")
        self.chk_diag.toggled.connect(self.diagonal_toggled)
        gl.addWidget(self.chk_diag)

        hint_lbl = QLabel("Drag Start/Goal, click to paint walls, Shift+click for weights")
        hint_lbl.setObjectName("dim")
        hint_lbl.setWordWrap(True)
        gl.addWidget(hint_lbl)
        layout.addWidget(self.grid_card)

        self.graph_card = QFrame()
        self.graph_card.setObjectName("card")
        grl = QVBoxLayout(self.graph_card)
        grl.setContentsMargins(12, 10, 12, 12)
        grl.setSpacing(8)

        graph_hdr = QLabel("GRAPH TOOLS")
        graph_hdr.setObjectName("section-title")
        grl.addWidget(graph_hdr)

        graph_row = QHBoxLayout()
        graph_row.setSpacing(6)
        btn_add_n = QPushButton("Add Node")
        btn_add_n.clicked.connect(self.add_node_requested)
        btn_add_e = QPushButton("Connect")
        btn_add_e.clicked.connect(self.add_edge_requested)
        graph_row.addWidget(btn_add_n)
        graph_row.addWidget(btn_add_e)
        grl.addLayout(graph_row)

        self.chk_directed = QCheckBox("Directed edges")
        self.chk_directed.toggled.connect(self.directed_toggled)
        grl.addWidget(self.chk_directed)

        ghint = QLabel("Drag nodes, double-click edge to edit cost, right-click for menu")
        ghint.setObjectName("dim")
        ghint.setWordWrap(True)
        grl.addWidget(ghint)
        layout.addWidget(self.graph_card)

        layout.addStretch()

    def _on_problem_changed(self, problem_type: str):
        self._sync_problem_controls(problem_type)
        self.problem_changed.emit(problem_type)

    def _sync_problem_controls(self, problem_type: str):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(preset_names(problem_type))
        self.preset_combo.blockSignals(False)

        self.heuristic_combo.blockSignals(True)
        self.heuristic_combo.clear()
        if problem_type == "Grid Pathfinding":
            self.heuristic_combo.addItems(["Manhattan", "Euclidean"])
        elif problem_type == "Graph Search":
            self.heuristic_combo.addItems(["Straight-Line (SLD)"])
        else:
            self.heuristic_combo.addItems(["Manhattan", "Misplaced Tiles"])
        self.heuristic_combo.blockSignals(False)
        if hasattr(self, "grid_card"):
            self.grid_card.setVisible(problem_type == "Grid Pathfinding")
        if hasattr(self, "graph_card"):
            self.graph_card.setVisible(problem_type == "Graph Search")

    def _on_algo_changed(self, name: str):
        self._sync_algo_controls(name)
        self.algorithm_changed.emit(name)

    def _sync_algo_controls(self, name: str):
        if not name:
            return
        info = algorithms.get(name)
        self.category_badge.setText(info.category)

        show_h = info.needs_heuristic
        self.heuristic_label.setVisible(show_h)
        self.heuristic_combo.setVisible(show_h)

        show_depth = "depth_limit" in info.params
        show_beam = "beam_width" in info.params
        self.depth_label.setVisible(show_depth)
        self.depth_limit_spin.setVisible(show_depth)
        self.beam_label.setVisible(show_beam)
        self.beam_width_spin.setVisible(show_beam)
        self.param_card.setVisible(show_depth or show_beam)

    def set_searching(self, searching: bool):
        self.run_btn.setEnabled(not searching)
        self.run_btn.setText("Searching..." if searching else "Run Search")
        self.reset_btn.setVisible(not searching)
        self.cancel_btn.setVisible(searching)
        self.cancel_btn.setEnabled(searching)

    def refresh_theme(self):
        self.title_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_BRIGHT};"
        )
        self.theme_btn.set_icon_type("moon" if current_theme() == "light" else "sun")

    def selected_algorithm(self) -> str:
        return self.algo_combo.currentText()

    def selected_heuristic(self) -> str:
        return self.heuristic_combo.currentText()

    def algorithm_params(self) -> dict:
        return {
            "depth_limit": self.depth_limit_spin.value(),
            "beam_width": self.beam_width_spin.value(),
        }
