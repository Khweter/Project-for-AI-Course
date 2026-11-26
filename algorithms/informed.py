from __future__ import annotations
import heapq
import time
from typing import Callable

from core.metrics import tracked_search
from core.node import SearchNode
from core.problem import Problem, State
from core.trace import EventKind, SearchResult, StepEvent
from algorithms.registry import register


@register(
    "Greedy Best-First",
    category="Informed",
    needs_heuristic=True,
    complete="No (finite graph: Yes)",
    optimal="No",
    time_complexity="O(b^m)",
    space_complexity="O(b^m)",
    notes="Fast but misled by deceptive heuristics; ignores path cost g(n).",
)
def greedy_best_first(
    problem: Problem,
    heuristic: Callable[[State], float] | None = None,
    record_trace: bool = True,
    max_trace_events: int | None = 15_000,
    timeout_sec: float | None = None,
    max_nodes: int | None = None,
    cancel_check: Callable[[], bool] | None = None,
    **kwargs,
) -> SearchResult:
    # Category: Informed Search
    # Frontier: Min-Heap Priority Queue (heapq)
    # Evaluation: f(n) = h(n) (heuristic estimate to goal only)
    h_fn = heuristic or problem.heuristic
    events: list[StepEvent] = []
    goal_node: SearchNode | None = None
    aborted_reason = ""
    trace_truncated = False
    t0 = time.perf_counter()

    def emit(ev: StepEvent):
        nonlocal trace_truncated
        if not record_trace:
            return
        if ev.kind == EventKind.GOAL_FOUND or max_trace_events is None or len(events) < max_trace_events:
            events.append(ev)
        else:
            trace_truncated = True

    with tracked_search() as metrics:
        counter = 0
        h_start = h_fn(problem.initial)
        start = SearchNode(state=problem.initial, h=h_start, _creation_order=counter)
        metrics.nodes_generated += 1

        frontier: list[tuple[float, int, SearchNode]] = [(h_start, counter, start)]
        explored: set[State] = set()
        seen: set[State] = {start.state}
        metrics.record_frontier(len(frontier))

        while frontier:
            if (metrics.nodes_expanded & 255) == 0:
                if cancel_check and cancel_check():
                    aborted_reason = "Cancelled"
                    break
                if timeout_sec is not None and (time.perf_counter() - t0) >= timeout_sec:
                    aborted_reason = "Timeout"
                    break
                if max_nodes is not None and metrics.nodes_expanded >= max_nodes:
                    aborted_reason = "Limit"
                    break

            # Pop node with smallest heuristic h(n)
            _, _, current = heapq.heappop(frontier)
            if current.state in explored:
                continue
            explored.add(current.state)
            metrics.nodes_expanded += 1
            parent_st = current.parent.state if current.parent else None
            emit(StepEvent(EventKind.EXPAND, current.state, g=current.g, h=current.h, f=current.f, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))

            # Goal test upon expansion
            if problem.goal_test(current.state):
                emit(StepEvent(EventKind.GOAL_FOUND, current.state, g=current.g, h=current.h, f=current.f, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))
                goal_node = current
                break

            # Evaluate each unseen neighbor by h(n) and push to priority queue
            for action in problem.actions(current.state):
                neighbor = problem.result(current.state, action)
                if neighbor in seen:
                    continue
                seen.add(neighbor)

                g_cost = current.g + problem.step_cost(current.state, action, neighbor)
                h_cost = h_fn(neighbor)
                f_cost = g_cost + h_cost
                counter += 1
                child = SearchNode(state=neighbor, parent=current, action=action, g=g_cost, h=h_cost, depth=current.depth + 1, _creation_order=counter)
                metrics.nodes_generated += 1
                heapq.heappush(frontier, (h_cost, counter, child))
                metrics.record_frontier(len(frontier))
                emit(StepEvent(EventKind.GENERATE, neighbor, g=g_cost, h=h_cost, f=f_cost, parent_state=current.state, frontier_size=len(frontier), visited_count=len(explored)))

    # Reconstruct path
    path = [n.state for n in goal_node.path()] if goal_node else []
    return SearchResult(
        algorithm="Greedy Best-First",
        path=path,
        path_cost=goal_node.g if goal_node else 0.0,
        nodes_expanded=metrics.nodes_expanded,
        nodes_generated=metrics.nodes_generated,
        max_frontier=metrics.max_frontier,
        elapsed_sec=metrics.elapsed_sec,
        peak_memory_bytes=metrics.peak_memory_bytes,
        success=goal_node is not None,
        aborted_reason=aborted_reason,
        trace_truncated=trace_truncated,
        events=events,
    )


@register(
    "A*",
    category="Informed",
    needs_heuristic=True,
    complete="Yes (if finite b)",
    optimal="Yes (admissible h)",
    time_complexity="O(b^d) worst",
    space_complexity="O(b^d)",
    notes="Optimal with admissible/consistent h; stores all generated nodes.",
)
def a_star(
    problem: Problem,
    heuristic: Callable[[State], float] | None = None,
    record_trace: bool = True,
    max_trace_events: int | None = 15_000,
    timeout_sec: float | None = None,
    max_nodes: int | None = None,
    cancel_check: Callable[[], bool] | None = None,
    **kwargs,
) -> SearchResult:
    # Category: Informed Search
    # Frontier: Min-Heap Priority Queue (heapq)
    # Evaluation: f(n) = g(n) + h(n) (path cost so far + heuristic estimate)
    h_fn = heuristic or problem.heuristic
    events: list[StepEvent] = []
    goal_node: SearchNode | None = None
    aborted_reason = ""
    trace_truncated = False
    t0 = time.perf_counter()

    def emit(ev: StepEvent):
        nonlocal trace_truncated
        if not record_trace:
            return
        if ev.kind == EventKind.GOAL_FOUND or max_trace_events is None or len(events) < max_trace_events:
            events.append(ev)
        else:
            trace_truncated = True

    with tracked_search() as metrics:
        counter = 0
        h_start = h_fn(problem.initial)
        start = SearchNode(state=problem.initial, h=h_start, _creation_order=counter)
        metrics.nodes_generated += 1

        frontier: list[SearchNode] = [start]
        best_g: dict[State, float] = {start.state: 0.0}
        explored: set[State] = set()
        metrics.record_frontier(len(frontier))

        while frontier:
            if (metrics.nodes_expanded & 255) == 0:
                if cancel_check and cancel_check():
                    aborted_reason = "Cancelled"
                    break
                if timeout_sec is not None and (time.perf_counter() - t0) >= timeout_sec:
                    aborted_reason = "Timeout"
                    break
                if max_nodes is not None and metrics.nodes_expanded >= max_nodes:
                    aborted_reason = "Limit"
                    break

            # Pop node with smallest f(n) = g(n) + h(n)
            current = heapq.heappop(frontier)
            if current.state in explored:
                continue
            explored.add(current.state)
            metrics.nodes_expanded += 1
            parent_st = current.parent.state if current.parent else None
            emit(StepEvent(EventKind.EXPAND, current.state, g=current.g, h=current.h, f=current.f, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))

            # Goal test when popped to guarantee optimality with admissible h
            if problem.goal_test(current.state):
                emit(StepEvent(EventKind.GOAL_FOUND, current.state, g=current.g, h=current.h, f=current.f, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))
                goal_node = current
                break

            # Compute g, h, f for neighbors and push if a cheaper path is found
            for action in problem.actions(current.state):
                neighbor = problem.result(current.state, action)
                if neighbor in explored:
                    continue

                g_cost = current.g + problem.step_cost(current.state, action, neighbor)
                if neighbor not in best_g or g_cost < best_g[neighbor]:
                    is_update = neighbor in best_g
                    best_g[neighbor] = g_cost
                    h_cost = h_fn(neighbor)
                    f_cost = g_cost + h_cost
                    counter += 1
                    child = SearchNode(state=neighbor, parent=current, action=action, g=g_cost, h=h_cost, depth=current.depth + 1, _creation_order=counter)
                    metrics.nodes_generated += 1
                    heapq.heappush(frontier, child)
                    metrics.record_frontier(len(frontier))
                    kind = EventKind.UPDATE if is_update else EventKind.GENERATE
                    emit(StepEvent(kind, neighbor, g=g_cost, h=h_cost, f=f_cost, parent_state=current.state, frontier_size=len(frontier), visited_count=len(explored)))

    # Reconstruct optimal path
    path = [n.state for n in goal_node.path()] if goal_node else []
    return SearchResult(
        algorithm="A*",
        path=path,
        path_cost=goal_node.g if goal_node else 0.0,
        nodes_expanded=metrics.nodes_expanded,
        nodes_generated=metrics.nodes_generated,
        max_frontier=metrics.max_frontier,
        elapsed_sec=metrics.elapsed_sec,
        peak_memory_bytes=metrics.peak_memory_bytes,
        success=goal_node is not None,
        aborted_reason=aborted_reason,
        trace_truncated=trace_truncated,
        events=events,
    )
