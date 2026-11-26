from __future__ import annotations
from typing import Callable
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QSplitter, QStatusBar,
    QStackedWidget, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut

import algorithms
from core.problem import Problem
from core.trace import SearchResult, StepEvent
from presets.scenarios import create_preset
from problems.grid_problem import (
    GridProblem,
    generate_maze_backtracker,
    generate_maze_prims,
)
from problems.graph_problem import GraphProblem
from problems.puzzle_problem import PuzzleProblem
from problems.io_loader import load_scenario, save_scenario
from ui.theme import build_stylesheet, current_theme, set_theme
from ui.widgets.control_panel import ControlPanel
from ui.widgets.metrics_panel import MetricsPanel
from ui.widgets.compare_dialog import CompareDialog
from ui.playback import PlaybackBar, PlaybackController
from ui.canvas.grid_view import GridView
from ui.canvas.graph_view import GraphView
from ui.canvas.puzzle_view import PuzzleView


class SearchWorker(QThread):

    finished_search = pyqtSignal(object)

    def __init__(
        self,
        fn: Callable,
        problem: Problem,
        heuristic: Callable | None,
        params: dict,
        parent=None,
    ):
        super().__init__(parent)
        self._fn = fn
        self._problem = problem
        self._heuristic = heuristic
        self._params = dict(params)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        result = self._fn(
            self._problem,
            heuristic=self._heuristic,
            record_trace=True,
            max_trace_events=15_000,
            timeout_sec=5.0,
            max_nodes=150_000,
            cancel_check=lambda: self._cancelled,
            **self._params,
        )
        self.finished_search.emit(result)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project for AI")
        self.setMinimumSize(1280, 740)
        sheet = build_stylesheet()
        if QApplication.instance() is not None:
            QApplication.instance().setStyleSheet(sheet)
        self.setStyleSheet(sheet)

        self.controller = PlaybackController(self)
        self._problem: Problem | None = None
        self._current_result: SearchResult | None = None
        self._search_worker: SearchWorker | None = None

        self._build_ui()
        self._connect_signals()
        self._build_statusbar()
        self._load_active_preset()

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.control_panel = ControlPanel()
        self.control_panel.setFixedWidth(295)
        splitter.addWidget(self.control_panel)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.grid_view = GridView()
        self.graph_view = GraphView()
        self.puzzle_view = PuzzleView()

        self.canvas_stack = QStackedWidget()
        self.canvas_stack.addWidget(self.grid_view)
        self.canvas_stack.addWidget(self.graph_view)
        self.canvas_stack.addWidget(self.puzzle_view)
        center_layout.addWidget(self.canvas_stack, stretch=1)

        self.playback = PlaybackBar()
        center_layout.addWidget(self.playback)

        splitter.addWidget(center)

        self.metrics_panel = MetricsPanel()
        self.metrics_panel.setFixedWidth(275)
        splitter.addWidget(self.metrics_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        self.setCentralWidget(splitter)

    def _connect_signals(self):
        self.playback.play_toggled.connect(self.controller.set_playing)
        self.playback.step_forward.connect(self.controller.step_forward)
        self.playback.step_backward.connect(self.controller.step_backward)
        self.playback.reset_requested.connect(self.controller.reset)
        self.playback.speed_changed.connect(self.controller.set_speed)
        self.playback.scrubber_moved.connect(self.controller.seek)
        self.playback.zoom_in_requested.connect(lambda: self._active_canvas().zoom_in())
        self.playback.zoom_out_requested.connect(lambda: self._active_canvas().zoom_out())
        self.playback.zoom_reset_requested.connect(lambda: self._active_canvas().reset_zoom())

        QShortcut(QKeySequence("Ctrl+="), self, activated=lambda: self._active_canvas().zoom_in())
        QShortcut(QKeySequence("Ctrl++"), self, activated=lambda: self._active_canvas().zoom_in())
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self._active_canvas().zoom_out())
        QShortcut(QKeySequence("Ctrl+0"), self, activated=lambda: self._active_canvas().reset_zoom())

        self.controller.position_changed.connect(self._on_position_changed)
        self.controller.state_changed.connect(self.playback.set_playing_state)
        self.controller.step_applied.connect(self._on_step_applied)
        self.controller.reset_done.connect(self._on_playback_reset)
        self.controller.finished.connect(self._on_playback_finished)

        self.control_panel.problem_changed.connect(self._on_problem_changed)
        self.control_panel.preset_changed.connect(self._load_active_preset)
        self.control_panel.algorithm_changed.connect(self._update_status_from_controls)
        self.control_panel.run_requested.connect(self.run_search)
        self.control_panel.cancel_requested.connect(self.cancel_search)
        self.control_panel.reset_requested.connect(self._on_full_reset)
        self.control_panel.maze_requested.connect(self._on_maze_requested)
        self.control_panel.clear_walls_requested.connect(self._on_clear_walls)
        self.control_panel.show_costs_toggled.connect(self.grid_view.set_show_costs)
        self.control_panel.diagonal_toggled.connect(self._on_diagonal_toggled)
        self.control_panel.compare_requested.connect(self.open_compare_dialog)
        self.control_panel.save_requested.connect(self.save_current_scenario)
        self.control_panel.add_node_requested.connect(self.graph_view.prompt_add_node)
        self.control_panel.add_edge_requested.connect(self.graph_view.prompt_add_edge)
        self.control_panel.directed_toggled.connect(self._on_directed_toggled)
        self.control_panel.theme_toggled.connect(self.toggle_theme)

        for view in (self.grid_view, self.graph_view, self.puzzle_view):
            view.node_hovered.connect(self.metrics_panel.inspect_node)
            view.problem_modified.connect(self._on_full_reset)

    def _active_canvas(self):
        return self.canvas_stack.currentWidget()

    def _on_problem_changed(self, problem_type: str):
        idx_map = {
            "Grid Pathfinding": 0,
            "Graph Search": 1,
            "8-Puzzle": 2,
        }
        self.canvas_stack.setCurrentIndex(idx_map.get(problem_type, 0))
        self._load_active_preset()

    def _load_active_preset(self):
        ptype = self.control_panel.problem_combo.currentText()
        pname = self.control_panel.preset_combo.currentText()
        if not pname:
            return
        self._problem = create_preset(ptype, pname)
        self._current_result = None
        self.controller.set_events([])
        self.playback.set_range(0)
        self.metrics_panel.clear()

        if isinstance(self._problem, GridProblem):
            self._problem.allow_diagonal = self.control_panel.chk_diag.isChecked()
            self.grid_view.set_problem(self._problem)
        elif isinstance(self._problem, GraphProblem):
            self.control_panel.chk_directed.blockSignals(True)
            self.control_panel.chk_directed.setChecked(self._problem.directed)
            self.control_panel.chk_directed.blockSignals(False)
            self.graph_view.set_problem(self._problem)
        elif isinstance(self._problem, PuzzleProblem):
            self.puzzle_view.set_problem(self._problem)

        self._update_status_from_controls()

    def _resolve_heuristic(self) -> Callable | None:
        if self._problem is None:
            return None
        choice = self.control_panel.selected_heuristic()
        if isinstance(self._problem, GridProblem):
            return self._problem.euclidean if choice == "Euclidean" else self._problem.manhattan
        if isinstance(self._problem, PuzzleProblem):
            return (
                self._problem.misplaced_tiles
                if choice == "Misplaced Tiles"
                else self._problem.manhattan
            )
        return self._problem.heuristic

    def run_search(self):
        if self._problem is None:
            return
        if self._search_worker is not None and self._search_worker.isRunning():
            return

        self._active_canvas().clear_search()
        self.controller.set_events([])
        self.playback.set_range(0)

        algo_name = self.control_panel.selected_algorithm()
        info = algorithms.get(algo_name)
        params = self.control_panel.algorithm_params()
        heuristic = self._resolve_heuristic() if info.needs_heuristic else None

        self.control_panel.set_searching(True)
        self.metrics_panel.set_searching()
        self.statusBar().showMessage(f"Searching ({algo_name})...")

        self._search_worker = SearchWorker(
            info.fn,
            self._problem,
            heuristic,
            params,
            parent=self,
        )
        self._search_worker.finished_search.connect(self._on_search_finished)
        self._search_worker.start()

    def cancel_search(self):
        if self._search_worker is not None and self._search_worker.isRunning():
            self._search_worker.cancel()
            self.control_panel.cancel_btn.setEnabled(False)
            self.statusBar().showMessage("Cancelling search...")

    def _on_search_finished(self, result: SearchResult):
        self.control_panel.set_searching(False)
        self._current_result = result
        self.metrics_panel.update_from_result(result)

        if result.aborted_reason == "Cancelled":
            self.statusBar().showMessage("Search cancelled")
            return

        self.controller.set_events(result.events)
        self.playback.set_range(len(result.events))

        if result.events:
            self.controller.play()
        elif result.success:
            self._active_canvas().set_path(result.path)
        else:
            self._update_status_from_controls()

    def _on_maze_requested(self, kind: str):
        if not isinstance(self._problem, GridProblem):
            return
        goal = next(iter(self._problem.goals)) if self._problem.goals else (
            self._problem.rows - 2,
            self._problem.cols - 2,
        )
        if kind == "prims":
            walls = generate_maze_prims(
                self._problem.rows, self._problem.cols, self._problem.initial, goal
            )
        else:
            walls = generate_maze_backtracker(
                self._problem.rows, self._problem.cols, self._problem.initial, goal
            )
        self._problem.walls = walls
        self._problem.weights.clear()
        self.grid_view.set_problem(self._problem)
        self._on_full_reset()

    def _on_clear_walls(self):
        if not isinstance(self._problem, GridProblem):
            return
        self._problem.walls.clear()
        self._problem.weights.clear()
        self.grid_view.set_problem(self._problem)
        self._on_full_reset()

    def _on_diagonal_toggled(self, enabled: bool):
        if isinstance(self._problem, GridProblem):
            self._problem.allow_diagonal = enabled
            self._on_full_reset()

    def _on_directed_toggled(self, enabled: bool):
        if isinstance(self._problem, GraphProblem):
            self._problem.set_directed(enabled)
            self.graph_view.set_problem(self._problem)
            self._on_full_reset()

    def open_compare_dialog(self):
        if self._problem is None:
            return
        dlg = CompareDialog(
            self._problem,
            heuristic=self._resolve_heuristic(),
            params=self.control_panel.algorithm_params(),
            parent=self,
        )
        dlg.exec()

    def load_custom_file(self, path: str):
        try:
            loaded = load_scenario(path)
        except Exception as exc:
            QMessageBox.warning(self, "Load Error", f"Could not load scenario:\n{exc}")
            return

        self._problem = loaded
        self._current_result = None
        self.controller.set_events([])
        self.playback.set_range(0)
        self.metrics_panel.clear()

        if isinstance(loaded, GridProblem):
            self.control_panel.problem_combo.blockSignals(True)
            self.control_panel.problem_combo.setCurrentText("Grid Pathfinding")
            self.control_panel._sync_problem_controls("Grid Pathfinding")
            self.control_panel.problem_combo.blockSignals(False)
            self.canvas_stack.setCurrentIndex(0)
            self.grid_view.set_problem(loaded)
        elif isinstance(loaded, GraphProblem):
            self.control_panel.problem_combo.blockSignals(True)
            self.control_panel.problem_combo.setCurrentText("Graph Search")
            self.control_panel._sync_problem_controls("Graph Search")
            self.control_panel.problem_combo.blockSignals(False)
            self.canvas_stack.setCurrentIndex(1)
            self.graph_view.set_problem(loaded)

        self.statusBar().showMessage(f"Loaded scenario: {path}")

    def save_current_scenario(self):
        if self._problem is None:
            return
        if isinstance(self._problem, PuzzleProblem):
            QMessageBox.information(self, "Save Scenario", "Save is supported for Grid and Graph scenarios.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Scenario", "scenario.json", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            save_scenario(path, self._problem)
            self.statusBar().showMessage(f"Saved scenario: {path}")
        except Exception as exc:
            QMessageBox.warning(self, "Save Error", f"Could not save scenario:\n{exc}")

    def _on_step_applied(self, index: int, event: StepEvent):
        self._active_canvas().apply_event(event)
        self.metrics_panel.inspect_event(event)
        self.statusBar().showMessage(
            f"Step {index}/{self.controller.total_steps} | {event.kind.name}: {event.state}"
        )

    def _on_position_changed(self, pos: int, total: int):
        self.playback.set_position(pos, total)
        if total > 0 and pos >= total and self._current_result and self._current_result.success:
            self._active_canvas().set_path(self._current_result.path)

    def _on_playback_reset(self):
        self._active_canvas().clear_search()
        self._update_status_from_controls()

    def _on_playback_finished(self):
        if self._current_result and self._current_result.success:
            self._active_canvas().set_path(self._current_result.path)
            suffix = " (trace capped at 15k)" if self._current_result.trace_truncated else ""
            self.statusBar().showMessage(
                f"Solved ({self._current_result.algorithm}) | Cost: {self._current_result.path_cost:.1f} | "
                f"Expanded: {self._current_result.nodes_expanded}{suffix}"
            )
        elif self._current_result and self._current_result.aborted_reason:
            self.statusBar().showMessage(
                f"Search stopped ({self._current_result.aborted_reason}) | "
                f"Expanded: {self._current_result.nodes_expanded}"
            )
        else:
            self.statusBar().showMessage("Search finished: no path found")

    def closeEvent(self, event):
        if self._search_worker is not None and self._search_worker.isRunning():
            self._search_worker.cancel()
            self._search_worker.wait(3000)
        super().closeEvent(event)

    def _on_full_reset(self):
        self._current_result = None
        self.controller.set_events([])
        self.playback.set_range(0)
        self._active_canvas().clear_search()
        self.metrics_panel.clear()
        self._update_status_from_controls()

    def _update_status_from_controls(self):
        prob = self.control_panel.problem_combo.currentText()
        algo = self.control_panel.selected_algorithm()
        self.statusBar().showMessage(f"Ready | {prob} | {algo}")

    def toggle_theme(self):
        new_mode = "dark" if current_theme() == "light" else "light"
        set_theme(new_mode)
        sheet = build_stylesheet()
        if QApplication.instance() is not None:
            QApplication.instance().setStyleSheet(sheet)
        self.setStyleSheet(sheet)
        self.control_panel.refresh_theme()
        self.metrics_panel.refresh_theme()
        self.grid_view.refresh_theme()
        self.graph_view.refresh_theme()
        self.puzzle_view.refresh_theme()
        for btn in (
            self.playback.btn_reset,
            self.playback.btn_step_back,
            self.playback.btn_play,
            self.playback.btn_step_fwd,
        ):
            btn.update()

    def _build_statusbar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)
        self._update_status_from_controls()
