from __future__ import annotations
import math
from typing import Sequence

from core.problem import Problem


class GraphProblem(Problem):

    def __init__(
        self,
        initial: str,
        goal: str | set[str],
        nodes: dict[str, tuple[float, float]] | None = None,
        edges: list[tuple[str, str, float]] | None = None,
        directed: bool = False,
        custom_heuristics: dict[str, float] | None = None,
    ):
        super().__init__(initial=initial, goal=goal)
        self.nodes: dict[str, tuple[float, float]] = dict(nodes) if nodes else {}
        self.directed = directed
        self.custom_heuristics: dict[str, float] = dict(custom_heuristics) if custom_heuristics else {}
        self.adj: dict[str, dict[str, float]] = {n: {} for n in self.nodes}

        if edges:
            for u, v, w in edges:
                self.add_edge(u, v, w)

    def add_node(self, name: str, pos: tuple[float, float] = (0.0, 0.0)):
        self.nodes[name] = pos
        self.adj.setdefault(name, {})

    def remove_node(self, name: str):
        self.nodes.pop(name, None)
        self.adj.pop(name, None)
        self.custom_heuristics.pop(name, None)
        for neighbors in self.adj.values():
            neighbors.pop(name, None)

    def rename_node(self, old_name: str, new_name: str):
        if old_name == new_name or old_name not in self.nodes or new_name in self.nodes:
            return
        self.nodes[new_name] = self.nodes.pop(old_name)
        if old_name in self.custom_heuristics:
            self.custom_heuristics[new_name] = self.custom_heuristics.pop(old_name)
        old_nbrs = self.adj.pop(old_name, {})
        self.adj[new_name] = {
            (new_name if k == old_name else k): w for k, w in old_nbrs.items()
        }
        for neighbors in self.adj.values():
            if old_name in neighbors:
                neighbors[new_name] = neighbors.pop(old_name)
        if self.initial == old_name:
            self.initial = new_name
        if old_name in self._goal:
            self._goal.discard(old_name)
            self._goal.add(new_name)

    def set_directed(self, directed: bool):
        if self.directed == directed:
            return
        edges = self.edge_list()
        self.directed = directed
        self.adj = {n: {} for n in self.nodes}
        for u, v, w in edges:
            self.add_edge(u, v, w)

    def add_edge(self, u: str, v: str, weight: float = 1.0):
        self.adj.setdefault(u, {})
        self.adj.setdefault(v, {})
        self.nodes.setdefault(u, (0.0, 0.0))
        self.nodes.setdefault(v, (0.0, 0.0))
        self.adj[u][v] = float(weight)
        if not self.directed:
            self.adj[v][u] = float(weight)

    def remove_edge(self, u: str, v: str):
        if u in self.adj:
            self.adj[u].pop(v, None)
        if not self.directed and v in self.adj:
            self.adj[v].pop(u, None)

    def edge_list(self) -> list[tuple[str, str, float]]:
        seen: set[tuple[str, str]] = set()
        result: list[tuple[str, str, float]] = []
        for u, nbrs in self.adj.items():
            for v, w in nbrs.items():
                key = (u, v) if self.directed else tuple(sorted((u, v)))
                if key not in seen:
                    seen.add(key)
                    result.append((u, v, w))
        return result

    def actions(self, state: str) -> Sequence[str]:
        return sorted(self.adj.get(state, {}).keys())

    def result(self, state: str, action: str) -> str:
        return action

    def step_cost(self, state: str, action: str, next_state: str) -> float:
        return self.adj.get(state, {}).get(next_state, 1.0)

    def euclidean_sld(self, state: str) -> float:
        if state not in self.nodes or not self._goal:
            return 0.0
        x1, y1 = self.nodes[state]
        dists = []
        for g in self._goal:
            if g in self.nodes:
                x2, y2 = self.nodes[g]
                dists.append(math.hypot(x2 - x1, y2 - y1))
        return min(dists) if dists else 0.0

    def heuristic(self, state: str) -> float:
        if state in self.custom_heuristics:
            return self.custom_heuristics[state]
        return self.euclidean_sld(state)
