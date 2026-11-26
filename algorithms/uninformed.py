from __future__ import annotations
from collections import deque
import heapq
from typing import Callable

from core.metrics import tracked_search
from core.node import SearchNode
from core.problem import Problem, State
from core.trace import EventKind, SearchResult, StepEvent
from algorithms.registry import register


@register(
    "BFS",
    category="Uninformed",
    complete="Yes (if finite b)",
    optimal="Yes (unit cost)",
    time_complexity="O(b^d)",
    space_complexity="O(b^d)",
    notes="Optimal when all step costs are equal; high memory usage.",
)
def bfs(
    problem: Problem,
    heuristic: Callable[[State], float] | None = None,
    **kwargs,
) -> SearchResult:
    # Category: Uninformed Search
    # Frontier: FIFO Queue (collections.deque)
    # Evaluation: expands shallowest unvisited nodes first (depth order)
    events: list[StepEvent] = []
    goal_node: SearchNode | None = None

    with tracked_search() as metrics:
        start = SearchNode(state=problem.initial)
        metrics.nodes_generated += 1

        if problem.goal_test(start.state):
            events.append(StepEvent(EventKind.GOAL_FOUND, start.state, frontier_size=0, visited_count=1))
            goal_node = start
        else:
            frontier: deque[SearchNode] = deque([start])
            explored: set[State] = {start.state}
            metrics.record_frontier(len(frontier))

            while frontier:
                # Pop oldest node from the front of the FIFO queue
                current = frontier.popleft()
                metrics.nodes_expanded += 1
                parent_st = current.parent.state if current.parent else None
                events.append(StepEvent(EventKind.EXPAND, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))

                # Generate unvisited neighbors and goal-test on generation
                for action in problem.actions(current.state):
                    neighbor = problem.result(current.state, action)
                    if neighbor in explored:
                        continue

                    g_cost = current.g + problem.step_cost(current.state, action, neighbor)
                    child = SearchNode(state=neighbor, parent=current, action=action, g=g_cost, depth=current.depth + 1)
                    metrics.nodes_generated += 1
                    explored.add(neighbor)

                    if problem.goal_test(neighbor):
                        events.append(StepEvent(EventKind.GOAL_FOUND, neighbor, g=g_cost, f=g_cost, parent_state=current.state, frontier_size=len(frontier), visited_count=len(explored)))
                        goal_node = child
                        break

                    frontier.append(child)
                    metrics.record_frontier(len(frontier))
                    events.append(StepEvent(EventKind.GENERATE, neighbor, g=g_cost, f=g_cost, parent_state=current.state, frontier_size=len(frontier), visited_count=len(explored)))

                if goal_node is not None:
                    break

    # Reconstruct path from initial state to goal
    path = [n.state for n in goal_node.path()] if goal_node else []
    return SearchResult(
        algorithm="BFS",
        path=path,
        path_cost=goal_node.g if goal_node else 0.0,
        nodes_expanded=metrics.nodes_expanded,
        nodes_generated=metrics.nodes_generated,
        max_frontier=metrics.max_frontier,
        elapsed_sec=metrics.elapsed_sec,
        peak_memory_bytes=metrics.peak_memory_bytes,
        success=goal_node is not None,
        events=events,
    )


@register(
    "DFS",
    category="Uninformed",
    complete="No (finite graph: Yes)",
    optimal="No",
    time_complexity="O(b^m)",
    space_complexity="O(bm)",
    notes="May loop in infinite spaces or dead ends; low memory O(bm).",
)
def dfs(
    problem: Problem,
    heuristic: Callable[[State], float] | None = None,
    **kwargs,
) -> SearchResult:
    # Category: Uninformed Search
    # Frontier: LIFO Stack (Python list)
    # Evaluation: expands deepest unvisited node first
    events: list[StepEvent] = []
    goal_node: SearchNode | None = None

    with tracked_search() as metrics:
        start = SearchNode(state=problem.initial)
        metrics.nodes_generated += 1
        frontier: list[SearchNode] = [start]
        explored: set[State] = set()
        metrics.record_frontier(len(frontier))

        while frontier:
            # Pop most recently pushed node from the LIFO stack
            current = frontier.pop()
            if current.state in explored:
                continue
            explored.add(current.state)
            metrics.nodes_expanded += 1
            parent_st = current.parent.state if current.parent else None
            events.append(StepEvent(EventKind.EXPAND, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))

            # Goal test upon expansion
            if problem.goal_test(current.state):
                events.append(StepEvent(EventKind.GOAL_FOUND, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))
                goal_node = current
                break

            # Push neighbors in reverse so the first action is popped first
            for action in reversed(list(problem.actions(current.state))):
                neighbor = problem.result(current.state, action)
                if neighbor in explored:
                    continue

                g_cost = current.g + problem.step_cost(current.state, action, neighbor)
                child = SearchNode(state=neighbor, parent=current, action=action, g=g_cost, depth=current.depth + 1)
                metrics.nodes_generated += 1
                frontier.append(child)
                metrics.record_frontier(len(frontier))
                events.append(StepEvent(EventKind.GENERATE, neighbor, g=g_cost, f=g_cost, parent_state=current.state, frontier_size=len(frontier), visited_count=len(explored)))

    # Reconstruct path from initial state to goal
    path = [n.state for n in goal_node.path()] if goal_node else []
    return SearchResult(
        algorithm="DFS",
        path=path,
        path_cost=goal_node.g if goal_node else 0.0,
        nodes_expanded=metrics.nodes_expanded,
        nodes_generated=metrics.nodes_generated,
        max_frontier=metrics.max_frontier,
        elapsed_sec=metrics.elapsed_sec,
        peak_memory_bytes=metrics.peak_memory_bytes,
        success=goal_node is not None,
        events=events,
    )


@register(
    "UCS",
    category="Uninformed",
    complete="Yes (step cost >= e > 0)",
    optimal="Yes",
    time_complexity="O(b^(1 + C*/e))",
    space_complexity="O(b^(1 + C*/e))",
    notes="Optimal for general positive edge weights; explores by path cost g(n).",
)
def ucs(
    problem: Problem,
    heuristic: Callable[[State], float] | None = None,
    **kwargs,
) -> SearchResult:
    # Category: Uninformed Search
    # Frontier: Min-Heap Priority Queue (heapq)
    # Evaluation: f(n) = g(n) (cumulative path cost from start)
    events: list[StepEvent] = []
    goal_node: SearchNode | None = None

    with tracked_search() as metrics:
        counter = 0
        start = SearchNode(state=problem.initial, _creation_order=counter)
        metrics.nodes_generated += 1
        frontier: list[SearchNode] = [start]
        best_cost: dict[State, float] = {start.state: 0.0}
        explored: set[State] = set()
        metrics.record_frontier(len(frontier))

        while frontier:
            # Pop lowest-g node from the priority queue
            current = heapq.heappop(frontier)
            if current.state in explored:
                continue
            explored.add(current.state)
            metrics.nodes_expanded += 1
            parent_st = current.parent.state if current.parent else None
            events.append(StepEvent(EventKind.EXPAND, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))

            # Goal test when popped so the lowest-cost path is guaranteed
            if problem.goal_test(current.state):
                events.append(StepEvent(EventKind.GOAL_FOUND, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(explored)))
                goal_node = current
                break

            # Relax outgoing edges and push improved paths
            for action in problem.actions(current.state):
                neighbor = problem.result(current.state, action)
                if neighbor in explored:
                    continue

                g_cost = current.g + problem.step_cost(current.state, action, neighbor)
                if neighbor not in best_cost or g_cost < best_cost[neighbor]:
                    is_update = neighbor in best_cost
                    best_cost[neighbor] = g_cost
                    counter += 1
                    child = SearchNode(state=neighbor, parent=current, action=action, g=g_cost, depth=current.depth + 1, _creation_order=counter)
                    metrics.nodes_generated += 1
                    heapq.heappush(frontier, child)
                    metrics.record_frontier(len(frontier))
                    kind = EventKind.UPDATE if is_update else EventKind.GENERATE
                    events.append(StepEvent(kind, neighbor, g=g_cost, f=g_cost, parent_state=current.state, frontier_size=len(frontier), visited_count=len(explored)))

    # Reconstruct optimal path
    path = [n.state for n in goal_node.path()] if goal_node else []
    return SearchResult(
        algorithm="UCS",
        path=path,
        path_cost=goal_node.g if goal_node else 0.0,
        nodes_expanded=metrics.nodes_expanded,
        nodes_generated=metrics.nodes_generated,
        max_frontier=metrics.max_frontier,
        elapsed_sec=metrics.elapsed_sec,
        peak_memory_bytes=metrics.peak_memory_bytes,
        success=goal_node is not None,
        events=events,
    )


@register(
    "Depth-Limited",
    category="Uninformed",
    params={"depth_limit": {"type": "int", "default": 50, "min": 1, "max": 1000}},
    complete="No (Yes if l >= d)",
    optimal="No",
    time_complexity="O(b^l)",
    space_complexity="O(bl)",
    notes="Fails if shallowest goal is deeper than depth limit l.",
)
def depth_limited(
    problem: Problem,
    heuristic: Callable[[State], float] | None = None,
    depth_limit: int = 50,
    **kwargs,
) -> SearchResult:
    # Category: Uninformed Search
    # Frontier: LIFO Stack (Python list) with max depth cutoff l
    # Evaluation: expands deepest node within depth_limit
    events: list[StepEvent] = []
    goal_node: SearchNode | None = None

    with tracked_search() as metrics:
        start = SearchNode(state=problem.initial)
        metrics.nodes_generated += 1
        frontier: list[SearchNode] = [start]
        best_depth: dict[State, int] = {start.state: 0}
        metrics.record_frontier(len(frontier))

        while frontier:
            # Pop from stack
            current = frontier.pop()
            metrics.nodes_expanded += 1
            parent_st = current.parent.state if current.parent else None
            events.append(StepEvent(EventKind.EXPAND, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(best_depth)))

            # Goal test
            if problem.goal_test(current.state):
                events.append(StepEvent(EventKind.GOAL_FOUND, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(best_depth)))
                goal_node = current
                break

            # Stop expanding once depth_limit is reached
            if current.depth >= depth_limit:
                events.append(StepEvent(EventKind.PRUNE, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(best_depth)))
                continue

            # Push neighbors if reached at a strictly shallower depth
            for action in reversed(list(problem.actions(current.state))):
                neighbor = problem.result(current.state, action)
                next_depth = current.depth + 1
                if neighbor in best_depth and best_depth[neighbor] <= next_depth:
                    continue

                best_depth[neighbor] = next_depth
                g_cost = current.g + problem.step_cost(current.state, action, neighbor)
                child = SearchNode(state=neighbor, parent=current, action=action, g=g_cost, depth=next_depth)
                metrics.nodes_generated += 1
                frontier.append(child)
                metrics.record_frontier(len(frontier))
                events.append(StepEvent(EventKind.GENERATE, neighbor, g=g_cost, f=g_cost, parent_state=current.state, frontier_size=len(frontier), visited_count=len(best_depth)))

    # Reconstruct path
    path = [n.state for n in goal_node.path()] if goal_node else []
    return SearchResult(
        algorithm="Depth-Limited",
        path=path,
        path_cost=goal_node.g if goal_node else 0.0,
        nodes_expanded=metrics.nodes_expanded,
        nodes_generated=metrics.nodes_generated,
        max_frontier=metrics.max_frontier,
        elapsed_sec=metrics.elapsed_sec,
        peak_memory_bytes=metrics.peak_memory_bytes,
        success=goal_node is not None,
        events=events,
    )


@register(
    "Iterative Deepening",
    category="Uninformed",
    params={"depth_limit": {"type": "int", "default": 50, "min": 1, "max": 1000}},
    complete="Yes (if finite b)",
    optimal="Yes (unit cost)",
    time_complexity="O(b^d)",
    space_complexity="O(bd)",
    notes="Combines BFS completeness/optimality with DFS O(bd) space.",
)
def iterative_deepening(
    problem: Problem,
    heuristic: Callable[[State], float] | None = None,
    depth_limit: int = 50,
    **kwargs,
) -> SearchResult:
    # Category: Uninformed Search
    # Frontier: LIFO Stack repeated for depth limits 0, 1, ..., depth_limit
    # Evaluation: iterative depth-first passes until goal or no cutoff
    events: list[StepEvent] = []
    goal_node: SearchNode | None = None

    with tracked_search() as metrics:
        for limit in range(depth_limit + 1):
            start = SearchNode(state=problem.initial)
            metrics.nodes_generated += 1
            frontier: list[SearchNode] = [start]
            best_depth: dict[State, int] = {start.state: 0}
            cutoff = False
            metrics.record_frontier(len(frontier))

            while frontier:
                # Pop from stack for the current depth limit pass
                current = frontier.pop()
                metrics.nodes_expanded += 1
                parent_st = current.parent.state if current.parent else None
                events.append(StepEvent(EventKind.EXPAND, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(best_depth)))

                # Goal test
                if problem.goal_test(current.state):
                    events.append(StepEvent(EventKind.GOAL_FOUND, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(best_depth)))
                    goal_node = current
                    break

                # Prune at current depth limit and mark that a cutoff occurred
                if current.depth >= limit:
                    cutoff = True
                    events.append(StepEvent(EventKind.PRUNE, current.state, g=current.g, f=current.g, parent_state=parent_st, frontier_size=len(frontier), visited_count=len(best_depth)))
                    continue

                # Push neighbors within the depth bound
                for action in reversed(list(problem.actions(current.state))):
                    neighbor = problem.result(current.state, action)
                    next_depth = current.depth + 1
                    if neighbor in best_depth and best_depth[neighbor] <= next_depth:
                        continue

                    best_depth[neighbor] = next_depth
                    g_cost = current.g + problem.step_cost(current.state, action, neighbor)
                    child = SearchNode(state=neighbor, parent=current, action=action, g=g_cost, depth=next_depth)
                    metrics.nodes_generated += 1
                    frontier.append(child)
                    metrics.record_frontier(len(frontier))
                    events.append(StepEvent(EventKind.GENERATE, neighbor, g=g_cost, f=g_cost, parent_state=current.state, frontier_size=len(frontier), visited_count=len(best_depth)))

            if goal_node is not None or not cutoff:
                break

    # Reconstruct path
    path = [n.state for n in goal_node.path()] if goal_node else []
    return SearchResult(
        algorithm="Iterative Deepening",
        path=path,
        path_cost=goal_node.g if goal_node else 0.0,
        nodes_expanded=metrics.nodes_expanded,
        nodes_generated=metrics.nodes_generated,
        max_frontier=metrics.max_frontier,
        elapsed_sec=metrics.elapsed_sec,
        peak_memory_bytes=metrics.peak_memory_bytes,
        success=goal_node is not None,
        events=events,
    )
