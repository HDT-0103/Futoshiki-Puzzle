from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SolverStats:
    algorithm: str = ""
    nodes_expanded: int = 0
    assignments_tried: int = 0
    consistency_checks: int = 0
    domain_reductions: int = 0
    propagation_steps: int = 0

    def as_dict(self) -> dict[str, int | str]:
        return {
            "algorithm": self.algorithm,
            "nodes_expanded": self.nodes_expanded,
            "assignments_tried": self.assignments_tried,
            "consistency_checks": self.consistency_checks,
            "domain_reductions": self.domain_reductions,
            "propagation_steps": self.propagation_steps,
        }
