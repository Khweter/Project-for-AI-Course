from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Hashable

State = Hashable


class EventKind(Enum):
    EXPAND = auto()
    GENERATE = auto()
    UPDATE = auto()
    PRUNE = auto()
    GOAL_FOUND = auto()


@dataclass(slots=True)
class StepEvent:
    kind: EventKind
    state: State
    g: float = 0.0
    h: float = 0.0
    f: float = 0.0
    parent_state: State | None = None
    frontier_size: int = 0
    visited_count: int = 0


@dataclass
class SearchResult:
    algorithm: str = ""
    problem_name: str = ""
    path: list[State] = field(default_factory=list)
    path_cost: float = 0.0
    nodes_expanded: int = 0
    nodes_generated: int = 0
    max_frontier: int = 0
    elapsed_sec: float = 0.0
    peak_memory_bytes: int = 0
    success: bool = False
    aborted_reason: str = ""
    trace_truncated: bool = False
    events: list[StepEvent] = field(default_factory=list)
