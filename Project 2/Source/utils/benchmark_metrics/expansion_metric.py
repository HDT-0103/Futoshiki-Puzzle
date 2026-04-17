from __future__ import annotations

from Source.logic.stats import SolverStats


def resolve_expansions(algo: str, solver_metric: object, stats: SolverStats) -> int:
    if isinstance(solver_metric, dict):
        return int(solver_metric.get("expansions", 0))

    if isinstance(solver_metric, (int, float)):
        if algo == "astar":
            return max(int(solver_metric), int(stats.nodes_expanded))
        if algo in {"bt", "bf"}:
            return int(solver_metric)
        if algo == "fc":
            return 0
        if algo == "bc":
            return int(solver_metric)

    if algo == "astar":
        return int(stats.nodes_expanded)

    return 0
