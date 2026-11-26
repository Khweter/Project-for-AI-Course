from __future__ import annotations
import random
from typing import Sequence

from core.problem import Problem

Board = tuple[int, ...]
DEFAULT_GOAL: Board = (1, 2, 3, 4, 5, 6, 7, 8, 0)


def inversion_count(board: Board) -> int:
    tiles = [t for t in board if t != 0]
    inv = 0
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            if tiles[i] > tiles[j]:
                inv += 1
    return inv


def is_solvable(board: Board, goal: Board = DEFAULT_GOAL) -> bool:
    if len(board) != 9 or set(board) != set(range(9)):
        return False
    return (inversion_count(board) % 2) == (inversion_count(goal) % 2)


def random_solvable(steps: int = 35, goal: Board = DEFAULT_GOAL, seed: int | None = None) -> Board:
    rng = random.Random(seed)
    state = list(goal)
    blank = state.index(0)
    prev_blank = -1

    for _ in range(steps):
        r, c = divmod(blank, 3)
        neighbors = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < 3 and 0 <= nc < 3:
                nxt = nr * 3 + nc
                if nxt != prev_blank:
                    neighbors.append(nxt)
        nxt = rng.choice(neighbors)
        state[blank], state[nxt] = state[nxt], state[blank]
        prev_blank = blank
        blank = nxt

    return tuple(state)


class PuzzleProblem(Problem):

    def __init__(
        self,
        initial: Board,
        goal: Board = DEFAULT_GOAL,
    ):
        if not is_solvable(initial, goal):
            raise ValueError(f"Unsolvable 8-puzzle state: {initial}")
        super().__init__(initial=tuple(initial), goal=tuple(goal))
        self.goal_board: Board = tuple(goal)
        self._goal_pos: dict[int, tuple[int, int]] = {
            tile: divmod(idx, 3)
            for idx, tile in enumerate(self.goal_board)
            if tile != 0
        }

    def actions(self, state: Board) -> Sequence[str]:
        r, c = divmod(state.index(0), 3)
        moves: list[str] = []
        if r > 0:
            moves.append("UP")
        if r < 2:
            moves.append("DOWN")
        if c > 0:
            moves.append("LEFT")
        if c < 2:
            moves.append("RIGHT")
        return moves

    def result(self, state: Board, action: str) -> Board:
        blank = state.index(0)
        r, c = divmod(blank, 3)
        deltas = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}
        dr, dc = deltas[action]
        target = (r + dr) * 3 + (c + dc)

        lst = list(state)
        lst[blank], lst[target] = lst[target], lst[blank]
        return tuple(lst)

    def manhattan(self, state: Board) -> float:
        dist = 0
        for idx, tile in enumerate(state):
            if tile == 0:
                continue
            r, c = divmod(idx, 3)
            gr, gc = self._goal_pos[tile]
            dist += abs(r - gr) + abs(c - gc)
        return float(dist)

    def misplaced_tiles(self, state: Board) -> float:
        return float(
            sum(
                1
                for idx, tile in enumerate(state)
                if tile != 0 and tile != self.goal_board[idx]
            )
        )

    def heuristic(self, state: Board) -> float:
        return self.manhattan(state)
