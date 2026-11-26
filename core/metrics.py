from __future__ import annotations
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class SearchMetrics:
    nodes_expanded: int = 0
    nodes_generated: int = 0
    max_frontier: int = 0
    elapsed_sec: float = 0.0
    peak_memory_bytes: int = 0

    def record_frontier(self, size: int):
        if size > self.max_frontier:
            self.max_frontier = size


@contextmanager
def tracked_search():
    metrics = SearchMetrics()
    tracemalloc.start()
    start = time.perf_counter()
    try:
        yield metrics
    finally:
        metrics.elapsed_sec = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        metrics.peak_memory_bytes = peak
        tracemalloc.stop()
