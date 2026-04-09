from __future__ import annotations

from typing import List, Optional, Tuple

from Source.logic.constraints import Domains, FutoshikiCSP
from Source.logic.stats import SolverStats
from Source.utils.parser import FutoshikiInstance

Goal = Tuple[int, int]  # Val(row, col, ?)


def _prove_goals(csp: FutoshikiCSP, domains: Domains, goals: List[Goal]) -> Optional[Domains]:
    if csp.stats is not None:
        csp.stats.nodes_expanded += 1

    if not csp.reduce_domains(domains):
        return None

    if not goals:
        if csp.all_constraints_satisfied(domains):
            return domains
        next_cell = csp.choose_unassigned_cell(domains)
        if next_cell is None:
            return None
        goals = [next_cell]

    r, c = goals[0]
    cell = (r, c)

    if len(domains[cell]) == 1:
        return _prove_goals(csp, domains, goals[1:])

    for value in sorted(domains[cell]):
        if csp.stats is not None:
            csp.stats.assignments_tried += 1
        child = csp.copy_domains(domains)
        child[cell] = {value}
        proved = _prove_goals(csp, child, goals[1:])
        if proved is not None:
            return proved

    return None


def solve_bc(instance: FutoshikiInstance, stats: Optional[SolverStats] = None):
    if stats is not None:
        stats.algorithm = "bc"
    csp = FutoshikiCSP(instance, stats=stats)
    domains = csp.initial_domains()
    goals: List[Goal] = [(r, c) for r in range(csp.n) for c in range(csp.n)]

    solved = _prove_goals(csp, domains, goals)
    if solved is None:
        raise ValueError("No solution found with backward chaining.")
    return csp.to_grid(solved)
