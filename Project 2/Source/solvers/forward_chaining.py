from __future__ import annotations

from collections import deque
from typing import Optional

from Source.logic.constraints import Domains, FutoshikiCSP
from Source.logic.stats import SolverStats
from Source.utils.parser import FutoshikiInstance
from Source.solvers.backtracking import solve_bt


def _forward_propagate(csp: FutoshikiCSP, domains: Domains) -> bool:
    """Forward chaining over domain facts until no new facts can be derived."""
    queue = deque(csp.cells)

    while queue:
        if csp.stats is not None:
            csp.stats.propagation_steps += 1
        cell = queue.popleft()
        current = set(domains[cell])
        reduced = {v for v in current if csp.is_assignment_consistent(domains, cell, v)}
        if not reduced:
            return False
        if reduced != current:
            domains[cell] = reduced
            for peer in csp.peers(cell):
                queue.append(peer)
            for other, _ in csp.inequality_neighbors(cell):
                queue.append(other)

        if len(domains[cell]) == 1:
            value = next(iter(domains[cell]))
            for peer in csp.peers(cell):
                if value in domains[peer] and len(domains[peer]) > 1:
                    domains[peer].remove(value)
                    if not domains[peer]:
                        return False
                    queue.append(peer)

    return True

def solve_fc(instance: FutoshikiInstance, stats: Optional[SolverStats] = None):
    if stats is not None:
        stats.algorithm = "fc"
    csp = FutoshikiCSP(instance, stats=stats)
    domains = csp.initial_domains()

    if stats is not None:
        stats.nodes_expanded += 1

    if not _forward_propagate(csp, domains):
        raise ValueError("Contradiction detected during forward chaining.")

    if csp.all_constraints_satisfied(domains):
        return csp.to_grid(domains)

    # Forward chaining may not fully decide all cells, so complete with BT.
    return solve_bt(instance, stats=stats)
