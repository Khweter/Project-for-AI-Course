from __future__ import annotations
import math
import time
from typing import Callable

from core.metrics import tracked_search
from core.node import SearchNode
from core.problem import Problem, State
from core.trace import EventKind, SearchResult, StepEvent
from algorithms.registry import register


@register(
    "Beam Search",
    category="Advanced",
    needs_heuristic=True,
    params={"beam_width": {"type": "int", "default": 3, "min": 1, "max": 500}},
    complete="No",
    optimal="No",
    time_complexity="O(k*b*d)",
    space_complexity="O(k*b)",
    notes="Prunes frontier to top k nodes per level; may prune optimal path.",
)
def beam_search(
    problem: Problem,
    heuristic: Callable[[State], float] | None = None,
    beam_width: int = 3,
    record_trace: bool = True,
    max_trace_events: int | None = 15_000,
    timeout_sec: float | None = None,
    max_nodes: int | None = None,
    cancel_check: Callable[[], bool] | None = None,
    **kwargs,
) -> SearchResult:
    # Category: Informed / Local-Beam Search
    # Frontier: Bounded level list of top beam_width nodes
    # Evaluation: f(n) = h(n) (keeps k best states at each depth level)
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
        start = SearchNode(state=problem.initial, h=h_fn(problem.initial))
        metrics.nodes_generated += 1
        frontier: list[SearchNode] = [start]
        explored: set[State] = {start.state}
        metrics.record_frontier(len(frontier))

        while frontier:
            candidates: list[SearchNode] = []

            # Expand every node in the current beam level
            for current in frontier:
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

                metrics.nodes_expanded += 1
                parent_st = current.parent.state if current.parent else None
                emit(StepEvent(EventKind.EXPAND, current.state, g=current.g, h=current.h, f=current.f, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))

                # Goal test
                if problem.goal_test(current.state):
                    emit(StepEvent(EventKind.GOAL_FOUND, current.state, g=current.g, h=current.h, f=current.f, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))
                    goal_node = current
                    break

                # Generate neighbors for the next level's candidate pool
                for action in problem.actions(current.state):
                    neighbor = problem.result(current.state, action)
                    if neighbor in explored:
                        continue
                    explored.add(neighbor)

                    g_cost = current.g + problem.step_cost(current.state, action, neighbor)
                    h_cost = h_fn(neighbor)
                    f_cost = g_cost + h_cost
                    child = SearchNode(state=neighbor, parent=current, action=action, g=g_cost, h=h_cost, depth=current.depth + 1)
                    metrics.nodes_generated += 1
                    candidates.append(child)
                    emit(StepEvent(EventKind.GENERATE, neighbor, g=g_cost, h=h_cost, f=f_cost, parent_state=current.state, frontier_size=len(candidates), visited_count=len(explored)))

            if goal_node is not None or aborted_reason:
                break

            # Sort candidates by h(n) and prune everything beyond beam_width
            candidates.sort(key=lambda n: n.h)
            if record_trace:
                for pruned in candidates[beam_width:]:
                    pruned_parent = pruned.parent.state if pruned.parent else None
                    emit(StepEvent(EventKind.PRUNE, pruned.state, g=pruned.g, h=pruned.h, f=pruned.f, parent_state=pruned_parent, frontier_size=min(len(candidates), beam_width), visited_count=len(explored)))

            frontier = candidates[:beam_width]
            metrics.record_frontier(len(frontier))

    # Reconstruct path
    path = [n.state for n in goal_node.path()] if goal_node else []
    return SearchResult(
        algorithm="Beam Search",
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
    "IDA*",
    category="Advanced",
    needs_heuristic=True,
    complete="Yes (if finite b)",
    optimal="Yes (admissible h)",
    time_complexity="O(b^d) worst",
    space_complexity="O(bd)",
    notes="A* optimality with linear O(bd) memory via iterative f-thresholds.",
)
def ida_star(
    problem: Problem,
    heuristic: Callable[[State], float] | None = None,
    record_trace: bool = True,
    max_trace_events: int | None = 15_000,
    timeout_sec: float | None = 5.0,
    max_nodes: int | None = 150_000,
    cancel_check: Callable[[], bool] | None = None,
    **kwargs,
) -> SearchResult:
    # Category: Informed Search (Memory-Bounded)
    # Frontier: Recursive DFS path stack with iterative f-cost threshold
    # Evaluation: f(n) = g(n) + h(n) (with per-iteration best_g pruning for cyclic graphs)
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
        start = SearchNode(state=problem.initial, h=h_fn(problem.initial))
        metrics.nodes_generated += 1
        threshold = start.f
        path_stack: list[SearchNode] = [start]
        on_path: set[State] = {start.state}

        def search(bound: float, iter_best_g: dict[State, float]) -> tuple[SearchNode | None, float]:
            nonlocal aborted_reason
            if aborted_reason:
                return None, math.inf

            if (metrics.nodes_expanded & 255) == 0:
                if cancel_check and cancel_check():
                    aborted_reason = "Cancelled"
                    return None, math.inf
                if timeout_sec is not None and (time.perf_counter() - t0) >= timeout_sec:
                    aborted_reason = "Timeout"
                    return None, math.inf
                if max_nodes is not None and metrics.nodes_expanded >= max_nodes:
                    aborted_reason = "Limit"
                    return None, math.inf

            current = path_stack[-1]
            metrics.record_frontier(len(path_stack))
            parent_st = current.parent.state if current.parent else None

            # Prune branch if f(n) exceeds the current threshold
            if current.f > bound:
                emit(StepEvent(EventKind.PRUNE, current.state, g=current.g, h=current.h, f=current.f, parent_state=parent_st, frontier_size=len(path_stack), visited_count=metrics.nodes_expanded))
                return None, current.f

            metrics.nodes_expanded += 1
            emit(StepEvent(EventKind.EXPAND, current.state, g=current.g, h=current.h, f=current.f, parent_state=parent_st, frontier_size=len(path_stack), visited_count=metrics.nodes_expanded))

            # Goal test
            if problem.goal_test(current.state):
                emit(StepEvent(EventKind.GOAL_FOUND, current.state, g=current.g, h=current.h, f=current.f, parent_state=parent_st, frontier_size=len(path_stack), visited_count=metrics.nodes_expanded))
                return current, bound

            min_exceeded = math.inf
            children: list[SearchNode] = []

            # Generate neighbors not on active path and not already reached cheaper in this iteration
            for action in problem.actions(current.state):
                neighbor = problem.result(current.state, action)
                if neighbor in on_path:
                    continue

                g_cost = current.g + problem.step_cost(current.state, action, neighbor)
                if neighbor in iter_best_g and iter_best_g[neighbor] <= g_cost:
                    continue
                iter_best_g[neighbor] = g_cost

                h_cost = h_fn(neighbor)
                f_cost = g_cost + h_cost
                child = SearchNode(state=neighbor, parent=current, action=action, g=g_cost, h=h_cost, depth=current.depth + 1)
                metrics.nodes_generated += 1
                children.append(child)
                emit(StepEvent(EventKind.GENERATE, neighbor, g=g_cost, h=h_cost, f=f_cost, parent_state=current.state, frontier_size=len(path_stack), visited_count=metrics.nodes_expanded))

            # Explore lowest-f children first and track minimum pruned f-cost
            children.sort(key=lambda n: n.f)
            for child in children:
                path_stack.append(child)
                on_path.add(child.state)
                found, next_bound = search(bound, iter_best_g)
                if found is not None:
                    return found, next_bound
                if aborted_reason:
                    on_path.remove(child.state)
                    path_stack.pop()
                    return None, math.inf
                if next_bound < min_exceeded:
                    min_exceeded = next_bound
                on_path.remove(child.state)
                path_stack.pop()

            return None, min_exceeded

        # Repeat DFS passes, raising the f-threshold each iteration
        while True:
            iter_best_g: dict[State, float] = {start.state: 0.0}
            found, next_threshold = search(threshold, iter_best_g)
            if found is not None:
                goal_node = found
                break
            if aborted_reason or math.isinf(next_threshold):
                break
            threshold = next_threshold

    # Reconstruct optimal path
    path = [n.state for n in goal_node.path()] if goal_node else []
    return SearchResult(
        algorithm="IDA*",
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
