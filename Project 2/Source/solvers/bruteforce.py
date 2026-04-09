from __future__ import annotations

from typing import Optional, Tuple

from Source.logic.constraints import Domains, FutoshikiCSP
from Source.logic.stats import SolverStats
from Source.utils.parser import FutoshikiInstance


def _first_unassigned(domains: Domains, n: int) -> Optional[Tuple[int, int]]:
    for r in range(n):
        for c in range(n):
            if len(domains[(r, c)]) > 1:
                return (r, c)
    return None


def _dfs(csp: FutoshikiCSP, domains: Domains) -> Optional[Domains]:
    if csp.stats is not None:
        csp.stats.nodes_expanded += 1

    if not csp.reduce_domains(domains):
        return None

    if csp.all_constraints_satisfied(domains):
        return domains

    cell = _first_unassigned(domains, csp.n)
    if cell is None:
        return None

    for value in range(1, csp.n + 1):
        if value not in domains[cell]:
            continue
        if csp.stats is not None:
            csp.stats.assignments_tried += 1
        child = csp.copy_domains(domains)
        child[cell] = {value}
        solved = _dfs(csp, child)
        if solved is not None:
            return solved

    return None


def solve_bf(instance: FutoshikiInstance, stats: Optional[SolverStats] = None):
    if stats is not None:
        stats.algorithm = "bf"
    csp = FutoshikiCSP(instance, stats=stats)
    domains = csp.initial_domains()
    solved = _dfs(csp, domains)
    if solved is None:
        raise ValueError("No solution found with brute force.")
    return csp.to_grid(solved)
