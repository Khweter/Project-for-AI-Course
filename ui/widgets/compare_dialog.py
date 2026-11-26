from __future__ import annotations
import csv
from typing import Callable

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QWidget, QFileDialog, QSplitter, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

import algorithms
from core.problem import Problem
from core.trace import SearchResult
from ui.theme import Colors, build_stylesheet


class CompareDialog(QDialog):

    def __init__(
        self,
        problem: Problem,
        heuristic: Callable | None = None,
        params: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Algorithm Benchmark")
        self.setMinimumSize(1040, 680)
        self.setStyleSheet(build_stylesheet())

        self._problem = problem
        self._heuristic = heuristic
        self._params = params or {}
        self._results: list[SearchResult] = []
        self._checks: dict[str, QCheckBox] = {}

        self._build_ui()
        self.run_benchmark()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("Multi-Algorithm Benchmark")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_BRIGHT};"
        )
        top.addWidget(title)
        top.addStretch()

        self.btn_run = QPushButton("Run Benchmark")
        self.btn_run.setObjectName("primary")
        self.btn_run.clicked.connect(self.run_benchmark)

        self.btn_csv = QPushButton("Export CSV")
        self.btn_csv.clicked.connect(self._export_csv)

        self.btn_png = QPushButton("Export PNG")
        self.btn_png.clicked.connect(self._export_png)

        for btn in (self.btn_run, self.btn_csv, self.btn_png):
            top.addWidget(btn)
        root.addLayout(top)

        body = QSplitter(Qt.Orientation.Horizontal)

        sidebar = QFrame()
        sidebar.setObjectName("card")
        sidebar.setFixedWidth(210)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(12, 10, 12, 12)
        sl.setSpacing(8)

        hdr = QLabel("ALGORITHMS")
        hdr.setObjectName("section-title")
        sl.addWidget(hdr)

        sel_row = QHBoxLayout()
        btn_all = QPushButton("All")
        btn_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_none = QPushButton("None")
        btn_none.clicked.connect(lambda: self._set_all_checked(False))
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)
        sl.addLayout(sel_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        chk_container = QWidget()
        chk_layout = QVBoxLayout(chk_container)
        chk_layout.setContentsMargins(0, 4, 0, 0)
        chk_layout.setSpacing(6)

        for info in algorithms.all_algorithms():
            cb = QCheckBox(info.name)
            cb.setChecked(True)
            self._checks[info.name] = cb
            chk_layout.addWidget(cb)
        chk_layout.addStretch()
        scroll.setWidget(chk_container)
        sl.addWidget(scroll)
        body.addWidget(sidebar)

        right_split = QSplitter(Qt.Orientation.Vertical)

        self.figure = Figure(figsize=(8, 3.6), dpi=100, facecolor=Colors.BG_PRIMARY)
        self.canvas = FigureCanvasQTAgg(self.figure)
        right_split.addWidget(self.canvas)

        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels([
            "Algorithm",
            "Class",
            "Status",
            "Path Cost",
            "Length",
            "Expanded",
            "Time (ms)",
            "Memory (KB)",
            "Complete",
            "Optimal",
            "Time Comp.",
            "Space Comp.",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {Colors.BG_SURFACE}; border: 1px solid {Colors.BORDER}; "
            f"gridline-color: {Colors.BORDER}; border-radius: 6px; }}"
            f"QHeaderView::section {{ background-color: {Colors.BG_ELEVATED}; color: {Colors.TEXT_DIM}; "
            f"border: none; border-bottom: 1px solid {Colors.BORDER}; padding: 6px; font-weight: 700; }}"
        )
        right_split.addWidget(self.table)
        right_split.setStretchFactor(0, 1)
        right_split.setStretchFactor(1, 1)

        body.addWidget(right_split)
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        root.addWidget(body, stretch=1)

        self.notes_label = QLabel("Select a row to view algorithm complexity & behavior notes")
        self.notes_label.setObjectName("dim")
        self.notes_label.setWordWrap(True)
        root.addWidget(self.notes_label)

    def _set_all_checked(self, checked: bool):
        for cb in self._checks.values():
            cb.setChecked(checked)

    def run_benchmark(self):
        self._results.clear()
        for info in algorithms.all_algorithms():
            if not self._checks[info.name].isChecked():
                continue
            h = self._heuristic if info.needs_heuristic else None
            res = info.fn(self._problem, heuristic=h, **self._params)
            self._results.append(res)

        self._populate_table()
        self._render_charts()

    def _populate_table(self):
        self.table.setRowCount(len(self._results))
        for row, res in enumerate(self._results):
            info = algorithms.get(res.algorithm)
            vals = [
                res.algorithm,
                info.category,
                "Solved" if res.success else "Failed",
                f"{res.path_cost:.1f}" if res.success else "--",
                str(len(res.path)) if res.success else "--",
                str(res.nodes_expanded),
                f"{res.elapsed_sec * 1000:.2f}",
                f"{res.peak_memory_bytes / 1024:.1f}",
                info.complete,
                info.optimal,
                info.time_complexity,
                info.space_complexity,
            ]
            for col, text in enumerate(vals):
                item = QTableWidgetItem(text)
                item.setToolTip(info.notes)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    if col in (0, 1, 8, 9, 10, 11)
                    else Qt.AlignmentFlag.AlignCenter
                )
                self.table.setItem(row, col, item)

    def _on_row_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if 0 <= idx < len(self._results):
            info = algorithms.get(self._results[idx].algorithm)
            self.notes_label.setText(
                f"{info.name}: Complete: {info.complete} | Optimal: {info.optimal} | "
                f"Time: {info.time_complexity} | Space: {info.space_complexity} — {info.notes}"
            )

    def _render_charts(self):
        self.figure.clear()
        if not self._results:
            self.canvas.draw()
            return

        names = [r.algorithm for r in self._results]
        short = [n.replace("Depth-Limited", "DLS").replace("Iterative Deepening", "IDS").replace("Greedy Best-First", "GBFS").replace("Beam Search", "Beam") for n in names]
        expanded = [r.nodes_expanded for r in self._results]
        times_ms = [r.elapsed_sec * 1000.0 for r in self._results]
        costs = [r.path_cost if r.success else 0.0 for r in self._results]

        specs = [
            ("Nodes Expanded", expanded, Colors.ACCENT),
            ("Time (ms)", times_ms, Colors.START),
            ("Path Cost", costs, Colors.ACCENT_WARM),
        ]

        for idx, (title, values, color) in enumerate(specs, start=1):
            ax = self.figure.add_subplot(1, 3, idx)
            ax.set_facecolor(Colors.BG_SURFACE)
            bars = ax.bar(short, values, color=color, width=0.6)
            ax.set_title(title, color=Colors.TEXT_BRIGHT, fontsize=10, fontweight="bold", pad=8)
            ax.tick_params(axis="x", colors=Colors.TEXT_DIM, labelsize=8, rotation=35)
            ax.tick_params(axis="y", colors=Colors.TEXT_DIM, labelsize=8)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            for spine in ("bottom", "left"):
                ax.spines[spine].set_color(Colors.BORDER_LIGHT)
            ax.grid(axis="y", color=Colors.BORDER, linestyle="--", linewidth=0.6, alpha=0.7)
            ax.set_axisbelow(True)

            for bar, val in zip(bars, values):
                if val > 0:
                    lbl = f"{val:.1f}" if isinstance(val, float) and val < 100 else f"{val:.0f}"
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height(),
                        lbl,
                        ha="center",
                        va="bottom",
                        color=Colors.TEXT,
                        fontsize=7,
                    )

        self.figure.tight_layout(pad=1.4)
        self.canvas.draw()

    def _export_csv(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Benchmark CSV", "benchmark.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Algorithm", "Class", "Success", "Path Cost", "Path Length",
                "Nodes Expanded", "Nodes Generated", "Max Frontier",
                "Time (ms)", "Peak Memory (bytes)",
                "Complete", "Optimal", "Time Complexity", "Space Complexity", "Notes",
            ])
            for r in self._results:
                info = algorithms.get(r.algorithm)
                writer.writerow([
                    r.algorithm,
                    info.category,
                    r.success,
                    r.path_cost,
                    len(r.path),
                    r.nodes_expanded,
                    r.nodes_generated,
                    r.max_frontier,
                    f"{r.elapsed_sec * 1000:.3f}",
                    r.peak_memory_bytes,
                    info.complete,
                    info.optimal,
                    info.time_complexity,
                    info.space_complexity,
                    info.notes,
                ])

    def _export_png(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Benchmark Chart", "benchmark.png", "PNG Images (*.png)"
        )
        if not path:
            return
        self.figure.savefig(path, dpi=150, facecolor=Colors.BG_PRIMARY)
