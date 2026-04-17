from __future__ import annotations

from Source.logic.stats import SolverStats


def resolve_inferences(algo: str, solver_metric: object, stats: SolverStats) -> int:
    if isinstance(solver_metric, dict):
        return int(solver_metric.get("inferences", 0))

    if isinstance(solver_metric, (int, float)):
        if algo in {"fc", "bc"}:
            return int(solver_metric)
        return 0

    if algo == "astar":
        return int(stats.consistency_checks + stats.propagation_steps)

    return 0
