from __future__ import annotations
from typing import Callable

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QWidget, QFileDialog, QSplitter, QScrollArea, QFrame,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QPixmap, QPainter, QFont, QPen

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

import algorithms
from core.problem import Problem
from core.trace import SearchResult
from ui.theme import Colors, build_stylesheet
from ui.widgets.spinbox import CleanDoubleSpinBox, CleanSpinBox


class BenchmarkWorker(QThread):

    progress = pyqtSignal(int, int, str)
    result_ready = pyqtSignal(object)
    finished_all = pyqtSignal(list)

    def __init__(
        self,
        problem: Problem,
        algo_names: list[str],
        heuristic: Callable | None = None,
        params: dict | None = None,
        timeout_sec: float = 3.0,
        max_nodes: int = 50000,
        parent=None,
    ):
        super().__init__(parent)
        self._problem = problem
        self._algo_names = list(algo_names)
        self._heuristic = heuristic
        self._params = dict(params or {})
        self._timeout_sec = timeout_sec
        self._max_nodes = max_nodes
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        results: list[SearchResult] = []
        total = len(self._algo_names)
        for idx, name in enumerate(self._algo_names, start=1):
            if self._cancelled:
                break
            self.progress.emit(idx, total, name)
            info = algorithms.get(name)
            h = self._heuristic if info.needs_heuristic else None
            res = info.fn(
                self._problem,
                heuristic=h,
                record_trace=False,
                timeout_sec=self._timeout_sec,
                max_nodes=self._max_nodes,
                cancel_check=lambda: self._cancelled,
                **self._params,
            )
            results.append(res)
            self.result_ready.emit(res)

        self.finished_all.emit(results)


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
        self.setMinimumSize(1080, 700)
        self.setStyleSheet(build_stylesheet())

        self._problem = problem
        self._heuristic = heuristic
        self._params = params or {}
        self._results: list[SearchResult] = []
        self._checks: dict[str, QCheckBox] = {}
        self._worker: BenchmarkWorker | None = None

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("Multi-Algorithm Benchmark")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_BRIGHT};"
        )
        top.addWidget(title)
        top.addStretch()

        top.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = CleanDoubleSpinBox()
        self.timeout_spin.setRange(0.5, 30.0)
        self.timeout_spin.setSingleStep(0.5)
        self.timeout_spin.setValue(3.0)
        self.timeout_spin.setFixedWidth(78)
        top.addWidget(self.timeout_spin)

        top.addWidget(QLabel("Max Nodes:"))
        self.max_nodes_spin = CleanSpinBox()
        self.max_nodes_spin.setRange(1000, 500000)
        self.max_nodes_spin.setSingleStep(10000)
        self.max_nodes_spin.setValue(50000)
        self.max_nodes_spin.setFixedWidth(98)
        top.addWidget(self.max_nodes_spin)

        self.btn_run = QPushButton("Run Comparison")
        self.btn_run.setObjectName("primary")
        self.btn_run.clicked.connect(self.run_benchmark)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_benchmark)

        self.btn_png = QPushButton("Export PNG")
        self.btn_png.clicked.connect(self._export_png)

        for btn in (self.btn_run, self.btn_cancel, self.btn_png):
            top.addWidget(btn)
        root.addLayout(top)

        prog_row = QHBoxLayout()
        prog_row.setSpacing(10)
        self.status_lbl = QLabel("Select algorithms and click Run Comparison")
        self.status_lbl.setObjectName("dim")
        prog_row.addWidget(self.status_lbl, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setFixedWidth(240)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ background-color: {Colors.BORDER}; border-radius: 4px; border: none; }}"
            f"QProgressBar::chunk {{ background-color: {Colors.ACCENT}; border-radius: 4px; }}"
        )
        prog_row.addWidget(self.progress_bar)
        root.addLayout(prog_row)

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
        if self._worker is not None and self._worker.isRunning():
            return

        selected = [
            info.name
            for info in algorithms.all_algorithms()
            if self._checks[info.name].isChecked()
        ]
        if not selected:
            self.status_lbl.setText("No algorithms selected")
            return

        self._results.clear()
        self.table.setRowCount(0)
        self.figure.clear()
        self.canvas.draw()

        self.progress_bar.setRange(0, len(selected))
        self.progress_bar.setValue(0)
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self._worker = BenchmarkWorker(
            problem=self._problem,
            algo_names=selected,
            heuristic=self._heuristic,
            params=self._params,
            timeout_sec=self.timeout_spin.value(),
            max_nodes=self.max_nodes_spin.value(),
            parent=self,
        )
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.result_ready.connect(self._on_worker_result)
        self._worker.finished_all.connect(self._on_worker_finished)
        self._worker.start()

    def cancel_benchmark(self):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self.status_lbl.setText("Cancelling...")
            self.btn_cancel.setEnabled(False)

    def _on_worker_progress(self, current: int, total: int, name: str):
        self.progress_bar.setValue(current - 1)
        self.status_lbl.setText(f"Running {name} ({current}/{total})...")

    def _on_worker_result(self, res: SearchResult):
        self._results.append(res)
        self._append_table_row(res)
        self.progress_bar.setValue(len(self._results))

    def _on_worker_finished(self, results: list[SearchResult]):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.status_lbl.setText(f"Completed {len(self._results)} algorithm(s)")
        self._render_charts()

    def _status_text(self, res: SearchResult) -> str:
        if res.aborted_reason:
            return res.aborted_reason
        return "Solved" if res.success else "Failed"

    def _append_table_row(self, res: SearchResult):
        row = self.table.rowCount()
        self.table.insertRow(row)
        info = algorithms.get(res.algorithm)
        status = self._status_text(res)
        vals = [
            res.algorithm,
            info.category,
            status,
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
            if col == 2:
                if status == "Solved":
                    item.setForeground(QColor(Colors.SUCCESS))
                elif status in ("Timeout", "Limit"):
                    item.setForeground(QColor(Colors.WARNING))
                else:
                    item.setForeground(QColor(Colors.ERROR))
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
        self.figure.set_facecolor(Colors.BG_PRIMARY)
        if not self._results:
            self.canvas.draw()
            return

        names = [r.algorithm for r in self._results]
        short = [
            n.replace("Depth-Limited", "DLS")
            .replace("Iterative Deepening", "IDS")
            .replace("Greedy Best-First", "GBFS")
            .replace("Beam Search", "Beam")
            for n in names
        ]
        expanded = [r.nodes_expanded for r in self._results]
        times_ms = [r.elapsed_sec * 1000.0 for r in self._results]
        costs = [r.path_cost if r.success else 0.0 for r in self._results]

        specs = [
            ("Nodes Expanded", expanded, Colors.ACCENT, False),
            ("Time (ms)", times_ms, Colors.START, False),
            ("Path Cost", costs, Colors.ACCENT_WARM, True),
        ]

        for idx, (title, values, color, is_cost) in enumerate(specs, start=1):
            ax = self.figure.add_subplot(1, 3, idx)
            ax.set_facecolor(Colors.BG_SURFACE)
            bar_colors = [
                Colors.BORDER_LIGHT if r.aborted_reason else color
                for r in self._results
            ]
            bars = ax.bar(short, values, color=bar_colors, width=0.6)
            ax.set_title(title, color=Colors.TEXT_BRIGHT, fontsize=10, fontweight="bold", pad=8)
            ax.tick_params(axis="x", colors=Colors.TEXT_DIM, labelsize=8, rotation=35)
            ax.tick_params(axis="y", colors=Colors.TEXT_DIM, labelsize=8)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            for spine in ("bottom", "left"):
                ax.spines[spine].set_color(Colors.BORDER_LIGHT)
            ax.grid(axis="y", color=Colors.BORDER, linestyle="--", linewidth=0.6, alpha=0.7)
            ax.set_axisbelow(True)

            for bar, val, res in zip(bars, values, self._results):
                if res.aborted_reason and is_cost:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        0,
                        res.aborted_reason[:3],
                        ha="center",
                        va="bottom",
                        color=Colors.WARNING,
                        fontsize=7,
                    )
                elif val > 0:
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

    def export_png_to(self, path: str):
        chart_pix = self.canvas.grab()
        col_count = self.table.columnCount()
        row_count = self.table.rowCount()

        col_widths = [max(78, self.table.columnWidth(c) + 12) for c in range(col_count)]
        table_w = sum(col_widths)
        row_h = 28
        hdr_h = 32
        pad = 16
        gap = 14

        total_w = max(chart_pix.width(), table_w) + 2 * pad
        table_h = hdr_h + row_count * row_h
        total_h = pad + chart_pix.height() + gap + table_h + pad

        out = QPixmap(total_w, total_h)
        out.fill(QColor(Colors.BG_PRIMARY))

        p = QPainter(out)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        chart_x = (total_w - chart_pix.width()) // 2
        p.drawPixmap(chart_x, pad, chart_pix)

        tx = (total_w - table_w) // 2
        ty = pad + chart_pix.height() + gap

        p.setPen(QPen(QColor(Colors.BORDER), 1))
        p.setBrush(QColor(Colors.BG_ELEVATED))
        p.drawRect(tx, ty, table_w, hdr_h)

        hdr_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        body_font = QFont("Segoe UI", 9)
        p.setFont(hdr_font)

        x = tx
        for c in range(col_count):
            w = col_widths[c]
            p.setPen(QColor(Colors.TEXT_DIM))
            hdr_text = self.table.horizontalHeaderItem(c).text()
            p.drawText(QRectF(x + 6, ty, w - 12, hdr_h), Qt.AlignmentFlag.AlignCenter, hdr_text)
            p.setPen(QPen(QColor(Colors.BORDER), 1))
            p.drawLine(x + w, ty, x + w, ty + hdr_h + row_count * row_h)
            x += w

        p.setFont(body_font)
        for r in range(row_count):
            ry = ty + hdr_h + r * row_h
            bg = QColor(Colors.BG_SURFACE if r % 2 == 0 else Colors.BG_SECONDARY)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRect(tx + 1, ry, table_w - 2, row_h)

            x = tx
            for c in range(col_count):
                w = col_widths[c]
                item = self.table.item(r, c)
                text = item.text() if item else ""
                if c == 2:
                    if text == "Solved":
                        p.setPen(QColor(Colors.SUCCESS))
                    elif text in ("Timeout", "Limit"):
                        p.setPen(QColor(Colors.WARNING))
                    else:
                        p.setPen(QColor(Colors.ERROR))
                else:
                    p.setPen(QColor(Colors.TEXT))
                align = (
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    if c in (0, 1, 8, 9, 10, 11)
                    else Qt.AlignmentFlag.AlignCenter
                )
                p.drawText(QRectF(x + 6, ry, w - 12, row_h), align, text)
                x += w

            p.setPen(QPen(QColor(Colors.BORDER), 1))
            p.drawLine(tx, ry + row_h, tx + table_w, ry + row_h)

        p.setPen(QPen(QColor(Colors.BORDER_LIGHT), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(tx, ty, table_w, table_h)
        p.end()

        out.save(path, "PNG")

    def _export_png(self):
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Benchmark PNG", "benchmark.png", "PNG Images (*.png)"
        )
        if not path:
            return
        self.export_png_to(path)

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        super().closeEvent(event)
