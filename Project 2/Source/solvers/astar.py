from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from Source.logic.constraints import Domains, FutoshikiCSP, domains_violation_lower_bound
from Source.logic.stats import SolverStats
from Source.utils.parser import FutoshikiInstance


@dataclass(order=True)
class PriorityState:
    f: int
    h: int
    g: int
    tie: int
    domains: Domains = field(compare=False)


def _state_signature(csp: FutoshikiCSP, domains: Domains) -> Tuple[Tuple[int, ...], ...]:
    return tuple(tuple(sorted(domains[(r, c)])) for r in range(csp.n) for c in range(csp.n))


def solve_astar(instance: FutoshikiInstance, stats: Optional[SolverStats] = None):
    if stats is not None:
        stats.algorithm = "astar"
    csp = FutoshikiCSP(instance, stats=stats)
    initial = csp.initial_domains()
    if not csp.reduce_domains(initial):
        raise ValueError("Initial state is inconsistent.")

    h0 = domains_violation_lower_bound(csp, initial)
    frontier: List[PriorityState] = []
    counter = 0
    heapq.heappush(frontier, PriorityState(f=h0, h=h0, g=0, tie=counter, domains=initial))
    visited = {}

    while frontier:
        if stats is not None:
            stats.nodes_expanded += 1
        current = heapq.heappop(frontier)
        sig = _state_signature(csp, current.domains)
        best_g = visited.get(sig)
        if best_g is not None and best_g <= current.g:
            continue
        visited[sig] = current.g

        if csp.all_constraints_satisfied(current.domains):
            return csp.to_grid(current.domains)

        cell = csp.choose_unassigned_cell(current.domains)
        if cell is None:
            continue

        for value in sorted(current.domains[cell]):
            if stats is not None:
                stats.assignments_tried += 1
            child = csp.copy_domains(current.domains)
            child[cell] = {value}
            if not csp.reduce_domains(child):
                continue

            g2 = current.g + 1
            h2 = domains_violation_lower_bound(csp, child)
            counter += 1
            heapq.heappush(frontier, PriorityState(f=g2 + h2, h=h2, g=g2, tie=counter, domains=child))

    raise ValueError("No solution found with A*.")
