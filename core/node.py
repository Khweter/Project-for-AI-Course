from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Hashable

State = Hashable
Action = Any


@dataclass(slots=True)
class SearchNode:
    state: State
    parent: SearchNode | None = None
    action: Action = None
    g: float = 0.0
    h: float = 0.0
    depth: int = 0
    _creation_order: int = field(default=0, repr=False)

    @property
    def f(self) -> float:
        return self.g + self.h

    def path(self) -> list[SearchNode]:
        node, chain = self, []
        while node:
            chain.append(node)
            node = node.parent
        chain.reverse()
        return chain

    def actions_path(self) -> list[Action]:
        return [n.action for n in self.path()[1:]]

    def __lt__(self, other: SearchNode) -> bool:
        # tie-break on insertion order for deterministic queue behavior
        if self.f != other.f:
            return self.f < other.f
        return self._creation_order < other._creation_order

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SearchNode):
            return NotImplemented
        return self.state == other.state

    def __hash__(self) -> int:
        return hash(self.state)
