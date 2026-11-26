from __future__ import annotations
import math
import random
from typing import Sequence

from core.problem import Problem, State

Coord = tuple[int, int]

CARDINAL_DIRS: tuple[Coord, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))
DIAGONAL_DIRS: tuple[Coord, ...] = ((-1, -1), (-1, 1), (1, -1), (1, 1))
_SQRT2 = math.sqrt(2)


class GridProblem(Problem):

    def __init__(
        self,
        rows: int = 20,
        cols: int = 20,
        initial: Coord = (1, 1),
        goal: Coord | set[Coord] = (18, 18),
        walls: set[Coord] | None = None,
        weights: dict[Coord, float] | None = None,
        allow_diagonal: bool = False,
    ):
        super().__init__(initial=initial, goal=goal)
        self.rows = rows
        self.cols = cols
        self.walls: set[Coord] = set(walls) if walls else set()
        self.weights: dict[Coord, float] = dict(weights) if weights else {}
        self.allow_diagonal = allow_diagonal

    def in_bounds(self, pos: Coord) -> bool:
        r, c = pos
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_passable(self, pos: Coord) -> bool:
        return self.in_bounds(pos) and pos not in self.walls

    def actions(self, state: Coord) -> Sequence[Coord]:
        r, c = state
        dirs = CARDINAL_DIRS + DIAGONAL_DIRS if self.allow_diagonal else CARDINAL_DIRS
        valid: list[Coord] = []
        for dr, dc in dirs:
            nxt = (r + dr, c + dc)
            if not self.is_passable(nxt):
                continue
            # Prevent cutting corners diagonally through adjacent walls
            if dr != 0 and dc != 0:
                if (r + dr, c) in self.walls or (r, c + dc) in self.walls:
                    continue
            valid.append(nxt)
        return valid

    def result(self, state: Coord, action: Coord) -> Coord:
        return action

    def step_cost(self, state: Coord, action: Coord, next_state: Coord) -> float:
        dr = abs(next_state[0] - state[0])
        dc = abs(next_state[1] - state[1])
        base = _SQRT2 if (dr == 1 and dc == 1) else 1.0
        return base * self.weights.get(next_state, 1.0)

    def manhattan(self, state: Coord) -> float:
        if not self._goal:
            return 0.0
        return min(abs(state[0] - g[0]) + abs(state[1] - g[1]) for g in self._goal)

    def euclidean(self, state: Coord) -> float:
        if not self._goal:
            return 0.0
        return min(math.hypot(state[0] - g[0], state[1] - g[1]) for g in self._goal)

    def heuristic(self, state: Coord) -> float:
        return self.euclidean(state) if self.allow_diagonal else self.manhattan(state)


def generate_maze_backtracker(
    rows: int,
    cols: int,
    start: Coord = (1, 1),
    goal: Coord | None = None,
    seed: int | None = None,
) -> set[Coord]:
    rng = random.Random(seed)
    walls: set[Coord] = {(r, c) for r in range(rows) for c in range(cols)}
    if goal is None:
        goal = (rows - 2 if rows % 2 == 1 else rows - 1, cols - 2 if cols % 2 == 1 else cols - 1)

    stack = [start]
    walls.discard(start)

    while stack:
        r, c = stack[-1]
        neighbors: list[tuple[Coord, Coord]] = []
        for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) in walls:
                neighbors.append(((nr, nc), (r + dr // 2, c + dc // 2)))

        if neighbors:
            nxt, mid = rng.choice(neighbors)
            walls.discard(mid)
            walls.discard(nxt)
            stack.append(nxt)
        else:
            stack.pop()

    walls.discard(start)
    walls.discard(goal)
    return walls


def generate_maze_prims(
    rows: int,
    cols: int,
    start: Coord = (1, 1),
    goal: Coord | None = None,
    seed: int | None = None,
) -> set[Coord]:
    rng = random.Random(seed)
    walls: set[Coord] = {(r, c) for r in range(rows) for c in range(cols)}
    if goal is None:
        goal = (rows - 2 if rows % 2 == 1 else rows - 1, cols - 2 if cols % 2 == 1 else cols - 1)

    walls.discard(start)
    frontier: list[tuple[Coord, Coord]] = []

    def add_frontier(cell: Coord):
        r, c = cell
        for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) in walls:
                frontier.append(((nr, nc), (r + dr // 2, c + dc // 2)))

    add_frontier(start)
    while frontier:
        idx = rng.randrange(len(frontier))
        nxt, mid = frontier.pop(idx)
        if nxt in walls:
            walls.discard(mid)
            walls.discard(nxt)
            add_frontier(nxt)

    walls.discard(start)
    walls.discard(goal)
    return walls
