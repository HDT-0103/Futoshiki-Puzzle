from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from math import inf
from typing import Dict, List, Optional, Tuple

from Source.logic.constraints import Domains, FutoshikiCSP
from Source.logic.stats import SolverStats
from Source.utils.parser import FutoshikiInstance


@dataclass(order=True)
class PriorityState:
    f: int
    g: int
    h: int
    tie: int
    domains: Domains = field(compare=False)


def _state_signature(csp: FutoshikiCSP, domains: Domains) -> Tuple[Tuple[int, ...], ...]:
    return tuple(tuple(sorted(domains[(r, c)])) for r in range(csp.n) for c in range(csp.n))


def _progress_cost(parent: Domains, child: Domains) -> int:
    """Edge cost under the progress model: number of newly fixed cells."""
    return _unassigned_count(parent) - _unassigned_count(child)


def _unassigned_count(domains: Domains) -> int:
    return sum(1 for vals in domains.values() if len(vals) > 1)


def _heuristic(domains: Domains) -> int:
    # h(s): number of currently unassigned cells.
    return _unassigned_count(domains)


def _astar_metrics(stats: SolverStats) -> dict[str, int]:
    # Inference work in A* is mostly done by domain propagation/consistency checks.
    return {
        "inferences": int(stats.consistency_checks + stats.propagation_steps),
        "expansions": int(stats.nodes_expanded),
    }


def solve_astar(instance: FutoshikiInstance, stats: Optional[SolverStats] = None) -> List[List[int]]:
    if stats is None:
        stats = SolverStats()
        
    if stats is not None:
        stats.algorithm = "astar"

    logs = []
    csp = FutoshikiCSP(instance, stats=stats)
    initial = csp.initial_domains()
    if not csp.reduce_domains(initial):
        #raise ValueError("Initial state is inconsistent.")
        logs.append("Initial state is inconsistent.")
        return None, _astar_metrics(stats), logs

    initial_sig = _state_signature(csp, initial)
    initial_u = _unassigned_count(initial)
    h0 = _heuristic(initial)
    frontier: List[PriorityState] = []
    counter = 0
    heapq.heappush(frontier, PriorityState(f=h0, h=h0, g=0, tie=counter, domains=initial))

    # Best known g-value for each state signature. With a consistent heuristic,
    # this supports optimal A* graph search without re-expanding dominated paths.
    best_g_by_sig: Dict[Tuple[Tuple[int, ...], ...], int] = {initial_sig: 0}

    while frontier:
        if stats is not None:
            stats.nodes_expanded += 1

        current = heapq.heappop(frontier)
        logs.append(f"Expand node #{stats.nodes_expanded}, f={current.f}, g={current.g}, h={current.h}")
        sig = _state_signature(csp, current.domains)

        # Skip stale queue entries that are dominated by a better discovered path.
        if current.g != best_g_by_sig.get(sig):
            continue

        if csp.all_constraints_satisfied(current.domains):
            logs.append(f"Solution found at node #{stats.nodes_expanded}")
            return csp.to_grid(current.domains), _astar_metrics(stats), logs


        cell = csp.choose_unassigned_cell(current.domains)
        if cell is None:
            continue

        for value in sorted(current.domains[cell]):
            if stats is not None:
                stats.assignments_tried += 1
            logs.append(f"  Try {cell} = {value}")
            child = csp.copy_domains(current.domains)
            child[cell] = {value}
            if not csp.reduce_domains(child):
                logs.append(f"    Pruned (arc inconsistent)")
                continue

            child_u = _unassigned_count(child)
            step_cost = _progress_cost(current.domains, child)
            if step_cost <= 0:
                continue

            # Under this model: g(s) = U(start) - U(s), h(s) = U(s), so f is constant (= U(start)).
            g2 = initial_u - child_u
            if g2 != current.g + step_cost:
                # Safety guard: keeps the proof assumptions aligned with implementation.
                continue

            h2 = _heuristic(child)
            sig2 = _state_signature(csp, child)

            if g2 >= best_g_by_sig.get(sig2, inf):
                continue

            best_g_by_sig[sig2] = g2
            counter += 1
            heapq.heappush(frontier, PriorityState(f=g2 + h2, h=h2, g=g2, tie=counter, domains=child))

    return None, _astar_metrics(stats), logs
