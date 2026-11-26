from __future__ import annotations
import json
from pathlib import Path

from core.problem import Problem
from problems.grid_problem import GridProblem
from problems.graph_problem import GraphProblem


def load_scenario(path: str | Path) -> Problem:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Scenario file not found: {p}")

    suffix = p.suffix.lower()
    if suffix == ".json":
        return _load_json(p)
    if suffix == ".txt":
        return _load_txt_grid(p)
    raise ValueError(f"Unsupported scenario format: {suffix}")


def save_scenario(path: str | Path, problem: Problem):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(problem, GridProblem):
        data = {
            "type": "grid",
            "rows": problem.rows,
            "cols": problem.cols,
            "start": list(problem.initial),
            "goals": [list(g) for g in sorted(problem.goals)],
            "walls": [list(w) for w in sorted(problem.walls)],
            "weights": {f"{r},{c}": w for (r, c), w in problem.weights.items()},
            "allow_diagonal": problem.allow_diagonal,
        }
    elif isinstance(problem, GraphProblem):
        data = {
            "type": "graph",
            "directed": problem.directed,
            "initial": problem.initial,
            "goals": sorted(problem.goals),
            "nodes": {name: list(pos) for name, pos in problem.nodes.items()},
            "edges": [[u, v, w] for u, v, w in problem.edge_list()],
            "custom_heuristics": problem.custom_heuristics,
        }
    else:
        raise ValueError(f"Unsupported problem type for export: {type(problem).__name__}")

    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_json(p: Path) -> Problem:
    data = json.loads(p.read_text(encoding="utf-8"))
    kind = data.get("type")

    if kind == "grid":
        rows = int(data["rows"])
        cols = int(data["cols"])
        start = tuple(data["start"])
        if "goals" in data:
            goal = {tuple(g) for g in data["goals"]}
        else:
            goal = tuple(data["goal"])
        walls = {tuple(w) for w in data.get("walls", [])}
        weights = {}
        for key, val in data.get("weights", {}).items():
            r, c = (int(x) for x in key.split(","))
            weights[(r, c)] = float(val)
        return GridProblem(
            rows=rows,
            cols=cols,
            initial=start,
            goal=goal,
            walls=walls,
            weights=weights,
            allow_diagonal=bool(data.get("allow_diagonal", False)),
        )

    if kind == "graph":
        nodes = {k: (float(v[0]), float(v[1])) for k, v in data["nodes"].items()}
        edges = [(str(u), str(v), float(w)) for u, v, w in data["edges"]]
        goals = set(data["goals"]) if "goals" in data else str(data["goal"])
        return GraphProblem(
            initial=str(data["initial"]),
            goal=goals,
            nodes=nodes,
            edges=edges,
            directed=bool(data.get("directed", False)),
            custom_heuristics=data.get("custom_heuristics"),
        )

    raise ValueError(f"Unknown scenario type in JSON: {kind!r}")


def _load_txt_grid(p: Path) -> GridProblem:
    lines = [line.rstrip("\r\n") for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError("Empty grid TXT file")

    rows = len(lines)
    cols = max(len(line) for line in lines)
    start = None
    goals: set[tuple[int, int]] = set()
    walls: set[tuple[int, int]] = set()

    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            if ch == "#":
                walls.add((r, c))
            elif ch == "S":
                start = (r, c)
            elif ch == "G":
                goals.add((r, c))

    if start is None or not goals:
        raise ValueError("Grid TXT must contain at least one 'S' (start) and 'G' (goal)")

    return GridProblem(rows=rows, cols=cols, initial=start, goal=goals, walls=walls)
