from __future__ import annotations
from typing import Callable

from core.problem import Problem
from problems.grid_problem import (
    GridProblem,
    generate_maze_backtracker,
    generate_maze_prims,
)
from problems.graph_problem import GraphProblem
from problems.puzzle_problem import PuzzleProblem, random_solvable


def _romania_map() -> GraphProblem:
    nodes = {
        "Arad": (40, 120),
        "Zerind": (65, 65),
        "Oradea": (105, 25),
        "Sibiu": (195, 130),
        "Timisoara": (55, 205),
        "Lugoj": (125, 240),
        "Mehadia": (135, 300),
        "Drobeta": (130, 360),
        "Craiova": (235, 365),
        "Rimnicu Vilcea": (235, 205),
        "Fagaras": (305, 130),
        "Pitesti": (325, 255),
        "Bucharest": (425, 320),
        "Giurgiu": (410, 390),
        "Urziceni": (495, 290),
        "Hirsova": (575, 290),
        "Eforie": (595, 355),
        "Vaslui": (540, 175),
        "Iasi": (505, 110),
        "Neamt": (435, 75),
    }
    edges = [
        ("Arad", "Zerind", 75),
        ("Arad", "Sibiu", 140),
        ("Arad", "Timisoara", 118),
        ("Zerind", "Oradea", 71),
        ("Oradea", "Sibiu", 151),
        ("Timisoara", "Lugoj", 111),
        ("Lugoj", "Mehadia", 70),
        ("Mehadia", "Drobeta", 75),
        ("Drobeta", "Craiova", 120),
        ("Craiova", "Rimnicu Vilcea", 146),
        ("Craiova", "Pitesti", 138),
        ("Sibiu", "Fagaras", 99),
        ("Sibiu", "Rimnicu Vilcea", 80),
        ("Rimnicu Vilcea", "Pitesti", 97),
        ("Fagaras", "Bucharest", 211),
        ("Pitesti", "Bucharest", 101),
        ("Bucharest", "Giurgiu", 90),
        ("Bucharest", "Urziceni", 85),
        ("Urziceni", "Hirsova", 98),
        ("Hirsova", "Eforie", 86),
        ("Urziceni", "Vaslui", 142),
        ("Vaslui", "Iasi", 92),
        ("Iasi", "Neamt", 87),
    ]
    sld_to_bucharest = {
        "Arad": 366,
        "Bucharest": 0,
        "Craiova": 160,
        "Drobeta": 242,
        "Eforie": 161,
        "Fagaras": 176,
        "Giurgiu": 77,
        "Hirsova": 151,
        "Iasi": 226,
        "Lugoj": 244,
        "Mehadia": 241,
        "Neamt": 234,
        "Oradea": 380,
        "Pitesti": 100,
        "Rimnicu Vilcea": 193,
        "Sibiu": 253,
        "Timisoara": 329,
        "Urziceni": 80,
        "Vaslui": 199,
        "Zerind": 374,
    }
    return GraphProblem(
        initial="Arad",
        goal="Bucharest",
        nodes=nodes,
        edges=edges,
        directed=False,
        custom_heuristics=sld_to_bucharest,
    )


def _multi_goal_graph() -> GraphProblem:
    nodes = {
        "Start": (60, 200),
        "A": (170, 100),
        "B": (170, 300),
        "C": (310, 90),
        "D": (310, 210),
        "E": (310, 320),
        "Goal1": (470, 120),
        "Goal2": (470, 290),
    }
    edges = [
        ("Start", "A", 3),
        ("Start", "B", 2),
        ("A", "C", 4),
        ("A", "D", 2),
        ("B", "D", 5),
        ("B", "E", 3),
        ("C", "Goal1", 6),
        ("D", "Goal1", 3),
        ("D", "Goal2", 4),
        ("E", "Goal2", 2),
    ]
    return GraphProblem(
        initial="Start",
        goal={"Goal1", "Goal2"},
        nodes=nodes,
        edges=edges,
        directed=False,
    )


def _heuristic_trap_graph() -> GraphProblem:
    nodes = {
        "S": (60, 200),
        "A": (200, 100),
        "B": (200, 300),
        "C": (350, 100),
        "G": (480, 200),
    }
    edges = [
        ("S", "A", 2),
        ("S", "B", 1),
        ("A", "C", 2),
        ("C", "G", 2),
        ("B", "G", 12),
    ]
    # B looks closer by h, but B->G edge is expensive (cost 12 vs S->A->C->G cost 6)
    heuristics = {"S": 6, "A": 4, "B": 2, "C": 2, "G": 0}
    return GraphProblem(
        initial="S",
        goal="G",
        nodes=nodes,
        edges=edges,
        directed=True,
        custom_heuristics=heuristics,
    )


def _open_grid() -> GridProblem:
    return GridProblem(rows=20, cols=20, initial=(2, 2), goal=(17, 17))


def _backtracker_maze() -> GridProblem:
    walls = generate_maze_backtracker(21, 21, start=(1, 1), goal=(19, 19), seed=42)
    return GridProblem(rows=21, cols=21, initial=(1, 1), goal=(19, 19), walls=walls)


def _prims_maze() -> GridProblem:
    walls = generate_maze_prims(21, 21, start=(1, 1), goal=(19, 19), seed=7)
    return GridProblem(rows=21, cols=21, initial=(1, 1), goal=(19, 19), walls=walls)


def _weighted_valley() -> GridProblem:
    weights: dict[tuple[int, int], float] = {}
    for r in range(3, 17):
        for c in range(7, 13):
            weights[(r, c)] = 5.0
    walls = {(r, 10) for r in range(0, 6)} | {(r, 10) for r in range(14, 20)}
    return GridProblem(
        rows=20,
        cols=20,
        initial=(10, 2),
        goal=(10, 17),
        walls=walls,
        weights=weights,
    )


def _puzzle_easy() -> PuzzleProblem:
    return PuzzleProblem((1, 2, 3, 4, 0, 5, 7, 8, 6))


def _puzzle_medium() -> PuzzleProblem:
    return PuzzleProblem((4, 1, 3, 7, 2, 5, 0, 8, 6))


def _puzzle_hard() -> PuzzleProblem:
    return PuzzleProblem((8, 6, 7, 2, 5, 4, 3, 0, 1))


def _puzzle_random() -> PuzzleProblem:
    return PuzzleProblem(random_solvable(steps=35))


PRESETS: dict[str, dict[str, Callable[[], Problem]]] = {
    "Grid Pathfinding": {
        "Open Grid (20x20)": _open_grid,
        "Backtracker Maze (21x21)": _backtracker_maze,
        "Prim's Maze (21x21)": _prims_maze,
        "Weighted Valley (20x20)": _weighted_valley,
    },
    "Graph Search": {
        "Romania Road Map (Arad -> Bucharest)": _romania_map,
        "Multi-Goal Graph": _multi_goal_graph,
        "Heuristic Trap Graph": _heuristic_trap_graph,
    },
    "8-Puzzle": {
        "Easy": _puzzle_easy,
        "Medium": _puzzle_medium,
        "Hard": _puzzle_hard,
        "Random Solvable": _puzzle_random,
    },
}


def preset_names(problem_type: str) -> list[str]:
    return list(PRESETS.get(problem_type, {}).keys())


def create_preset(problem_type: str, name: str) -> Problem:
    factory = PRESETS[problem_type][name]
    return factory()
