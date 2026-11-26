from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Hashable, Sequence

State = Hashable
Action = Any


class Problem(ABC):

    def __init__(self, initial: State, goal: State | set[State] | None = None):
        self.initial = initial
        self._goal = goal if isinstance(goal, set) else ({goal} if goal is not None else set())

    @abstractmethod
    def actions(self, state: State) -> Sequence[Action]:
        ...

    @abstractmethod
    def result(self, state: State, action: Action) -> State:
        ...

    def step_cost(self, state: State, action: Action, next_state: State) -> float:
        return 1.0

    def goal_test(self, state: State) -> bool:
        return state in self._goal

    def heuristic(self, state: State) -> float:
        return 0.0

    @property
    def goals(self) -> set[State]:
        return self._goal
