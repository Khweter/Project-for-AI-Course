from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any

_registry: dict[str, AlgorithmInfo] = {}


@dataclass
class AlgorithmInfo:
    name: str
    fn: Callable
    category: str
    needs_heuristic: bool = False
    params: dict[str, Any] = field(default_factory=dict)
    complete: str = ""
    optimal: str = ""
    time_complexity: str = ""
    space_complexity: str = ""
    notes: str = ""


def register(
    name: str,
    *,
    category: str,
    needs_heuristic: bool = False,
    params: dict[str, Any] | None = None,
    complete: str = "",
    optimal: str = "",
    time_complexity: str = "",
    space_complexity: str = "",
    notes: str = "",
):
    def decorator(fn: Callable) -> Callable:
        _registry[name] = AlgorithmInfo(
            name=name,
            fn=fn,
            category=category,
            needs_heuristic=needs_heuristic,
            params=params or {},
            complete=complete,
            optimal=optimal,
            time_complexity=time_complexity,
            space_complexity=space_complexity,
            notes=notes,
        )
        return fn
    return decorator


def get(name: str) -> AlgorithmInfo:
    return _registry[name]


def all_algorithms() -> list[AlgorithmInfo]:
    return list(_registry.values())


def by_category(category: str) -> list[AlgorithmInfo]:
    return [a for a in _registry.values() if a.category == category]


def names() -> list[str]:
    return list(_registry.keys())
