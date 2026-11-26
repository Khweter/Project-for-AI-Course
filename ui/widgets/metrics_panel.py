from __future__ import annotations
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFormLayout, QWidget,
)
from PyQt6.QtCore import Qt

from core.trace import SearchResult, StepEvent
from ui.theme import Colors, SPACING


class KpiCard(QFrame):

    def __init__(self, label: str, initial: str = "--", parent=None):
        super().__init__(parent)
        self.setObjectName("kpi-card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        desc = QLabel(label)
        desc.setObjectName("kpi-label")
        layout.addWidget(desc)

        self.value_label = QLabel(initial)
        self.value_label.setObjectName("kpi-value")
        layout.addWidget(self.value_label)

    def set_value(self, text: str):
        self.value_label.setText(text)


class MetricsPanel(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inspector-dock")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        top = QHBoxLayout()
        self.header_lbl = QLabel("Inspector")
        self.header_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_BRIGHT};"
        )
        top.addWidget(self.header_lbl)
        top.addStretch()

        self.status_badge = QLabel("Ready")
        self.status_badge.setObjectName("mono-badge")
        top.addWidget(self.status_badge)
        layout.addLayout(top)

        perf_label = QLabel("PERFORMANCE")
        perf_label.setObjectName("section-title")
        layout.addWidget(perf_label)

        grid = QGridLayout()
        grid.setSpacing(8)

        self.kpi_time = KpiCard("TIME (MS)")
        self.kpi_visited = KpiCard("EXPANDED")
        self.kpi_frontier = KpiCard("MAX FRONTIER")
        self.kpi_memory = KpiCard("PEAK MEMORY")
        self.kpi_cost = KpiCard("PATH COST")
        self.kpi_depth = KpiCard("PATH LENGTH")

        grid.addWidget(self.kpi_time, 0, 0)
        grid.addWidget(self.kpi_visited, 0, 1)
        grid.addWidget(self.kpi_frontier, 1, 0)
        grid.addWidget(self.kpi_memory, 1, 1)
        grid.addWidget(self.kpi_cost, 2, 0)
        grid.addWidget(self.kpi_depth, 2, 1)
        layout.addLayout(grid)

        inspect_card = QFrame()
        inspect_card.setObjectName("card")
        il = QVBoxLayout(inspect_card)
        il.setContentsMargins(12, 10, 12, 12)
        il.setSpacing(8)

        insp_hdr = QLabel("NODE INSPECTOR")
        insp_hdr.setObjectName("section-title")
        il.addWidget(insp_hdr)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)

        self.lbl_state = self._mono_label("--")
        self.lbl_g = self._mono_label("--")
        self.lbl_h = self._mono_label("--")
        self.lbl_f = self._mono_label("--")
        self.lbl_parent = self._mono_label("--")

        form.addRow("State", self.lbl_state)
        form.addRow("g(n)", self.lbl_g)
        form.addRow("h(n)", self.lbl_h)
        form.addRow("f(n)", self.lbl_f)
        form.addRow("Parent", self.lbl_parent)
        il.addLayout(form)
        layout.addWidget(inspect_card)

        legend_card = QFrame()
        legend_card.setObjectName("card")
        ll = QVBoxLayout(legend_card)
        ll.setContentsMargins(12, 10, 12, 12)
        ll.setSpacing(8)

        leg_hdr = QLabel("LEGEND")
        leg_hdr.setObjectName("section-title")
        ll.addWidget(leg_hdr)

        leg_grid = QGridLayout()
        leg_grid.setSpacing(6)
        self._swatches: list[tuple[str, QFrame]] = []
        items = [
            ("Start", "START"),
            ("Goal", "GOAL"),
            ("Frontier", "FRONTIER"),
            ("Visited", "VISITED"),
            ("Path", "PATH"),
            ("Wall", "WALL"),
        ]
        for idx, (label, attr) in enumerate(items):
            row_w = QWidget()
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
            swatch = QFrame()
            swatch.setFixedSize(11, 11)
            swatch.setStyleSheet(
                f"background-color: {getattr(Colors, attr)}; border-radius: 3px; border: 1px solid {Colors.BORDER_LIGHT};"
            )
            self._swatches.append((attr, swatch))
            rl.addWidget(swatch)
            txt = QLabel(label)
            txt.setObjectName("dim")
            rl.addWidget(txt)
            rl.addStretch()
            leg_grid.addWidget(row_w, idx // 2, idx % 2)
        ll.addLayout(leg_grid)
        layout.addWidget(legend_card)

        layout.addStretch()

    def _mono_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-family: 'Cascadia Code', monospace; color: {Colors.TEXT_BRIGHT};"
        )
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    def inspect_event(self, event: StepEvent):
        self.lbl_state.setText(str(event.state))
        self.lbl_g.setText(f"{event.g:.2f}")
        self.lbl_h.setText(f"{event.h:.2f}")
        self.lbl_f.setText(f"{event.f:.2f}")
        self.lbl_parent.setText(str(event.parent_state) if event.parent_state is not None else "--")

    def inspect_node(self, state, g: float, h: float, parent=None):
        self.lbl_state.setText(str(state))
        self.lbl_g.setText(f"{g:.2f}")
        self.lbl_h.setText(f"{h:.2f}")
        self.lbl_f.setText(f"{g + h:.2f}")
        self.lbl_parent.setText(str(parent) if parent is not None else "--")

    def set_searching(self):
        self.status_badge.setText("Searching...")
        self.status_badge.setStyleSheet(
            f"color: {Colors.WARNING}; background-color: {Colors.BG_ELEVATED}; "
            f"border: 1px solid {Colors.WARNING}; border-radius: 4px; padding: 2px 6px;"
        )

    def update_from_result(self, result: SearchResult):
        self.kpi_time.set_value(f"{result.elapsed_sec * 1000:.2f}")
        self.kpi_visited.set_value(str(result.nodes_expanded))
        self.kpi_frontier.set_value(str(result.max_frontier))
        mem_kb = result.peak_memory_bytes / 1024
        self.kpi_memory.set_value(f"{mem_kb:.1f} KB")
        self.kpi_cost.set_value(f"{result.path_cost:.1f}" if result.success else "--")
        self.kpi_depth.set_value(str(len(result.path)) if result.success else "0")

        if result.success:
            self.status_badge.setText("Solved")
            self.status_badge.setStyleSheet(
                f"color: {Colors.SUCCESS}; background-color: {Colors.BG_ELEVATED}; "
                f"border: 1px solid {Colors.SUCCESS}; border-radius: 4px; padding: 2px 6px;"
            )
        elif result.aborted_reason:
            self.status_badge.setText(result.aborted_reason)
            self.status_badge.setStyleSheet(
                f"color: {Colors.WARNING}; background-color: {Colors.BG_ELEVATED}; "
                f"border: 1px solid {Colors.WARNING}; border-radius: 4px; padding: 2px 6px;"
            )
        else:
            self.status_badge.setText("No Path")
            self.status_badge.setStyleSheet(
                f"color: {Colors.ERROR}; background-color: {Colors.BG_ELEVATED}; "
                f"border: 1px solid {Colors.ERROR}; border-radius: 4px; padding: 2px 6px;"
            )

    def refresh_theme(self):
        self.header_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_BRIGHT};"
        )
        for lbl in (self.lbl_state, self.lbl_g, self.lbl_h, self.lbl_f, self.lbl_parent):
            lbl.setStyleSheet(
                f"font-family: 'Cascadia Code', monospace; color: {Colors.TEXT_BRIGHT};"
            )
        for attr, swatch in self._swatches:
            swatch.setStyleSheet(
                f"background-color: {getattr(Colors, attr)}; border-radius: 3px; border: 1px solid {Colors.BORDER_LIGHT};"
            )

    def clear(self):
        for card in (
            self.kpi_time,
            self.kpi_visited,
            self.kpi_frontier,
            self.kpi_memory,
            self.kpi_cost,
            self.kpi_depth,
        ):
            card.set_value("--")
        for lbl in (self.lbl_state, self.lbl_g, self.lbl_h, self.lbl_f, self.lbl_parent):
            lbl.setText("--")
        self.status_badge.setText("Ready")
        self.status_badge.setStyleSheet("")
        self.status_badge.setObjectName("mono-badge")
