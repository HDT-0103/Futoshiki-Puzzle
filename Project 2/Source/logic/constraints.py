from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from Source.logic.stats import SolverStats
from Source.utils.parser import FutoshikiInstance

Cell = Tuple[int, int]
Domains = Dict[Cell, Set[int]]


class FutoshikiCSP:
    def __init__(self, instance: FutoshikiInstance, stats: Optional[SolverStats] = None) -> None:
        self.instance = instance
        self.n = instance.n
        self.cells: List[Cell] = [(r, c) for r in range(self.n) for c in range(self.n)]
        self.stats = stats

    def initial_domains(self) -> Domains:
        domains: Domains = {}
        for r, c in self.cells:
            v = self.instance.grid[r][c]
            if v == 0:
                domains[(r, c)] = set(range(1, self.n + 1))
            else:
                domains[(r, c)] = {v}
        return domains

    def peers(self, cell: Cell) -> Set[Cell]:
        r, c = cell
        out: Set[Cell] = set()
        for cc in range(self.n):
            if cc != c:
                out.add((r, cc))
        for rr in range(self.n):
            if rr != r:
                out.add((rr, c))
        return out

    def inequality_neighbors(self, cell: Cell) -> List[Tuple[Cell, int]]:
        r, c = cell
        out: List[Tuple[Cell, int]] = []

        if c < self.n - 1:
            sign = self.instance.h_constraints[r][c]
            if sign != 0:
                out.append(((r, c + 1), sign))
        if c > 0:
            sign = self.instance.h_constraints[r][c - 1]
            if sign != 0:
                out.append(((r, c - 1), -sign))

        if r < self.n - 1:
            sign = self.instance.v_constraints[r][c]
            if sign != 0:
                out.append(((r + 1, c), sign))
        if r > 0:
            sign = self.instance.v_constraints[r - 1][c]
            if sign != 0:
                out.append(((r - 1, c), -sign))

        return out

    @staticmethod
    def relation_holds(left: int, right: int, sign: int) -> bool:
        if sign == 1:
            return left < right
        if sign == -1:
            return left > right
        return True

    def is_pair_consistent(self, cell_a: Cell, val_a: int, cell_b: Cell, val_b: int) -> bool:
        ra, ca = cell_a
        rb, cb = cell_b

        if ra == rb and ca != cb and val_a == val_b:
            return False
        if ca == cb and ra != rb and val_a == val_b:
            return False

        if ra == rb and abs(ca - cb) == 1:
            left_c = min(ca, cb)
            sign = self.instance.h_constraints[ra][left_c]
            if sign != 0:
                if ca < cb:
                    return self.relation_holds(val_a, val_b, sign)
                return self.relation_holds(val_b, val_a, sign)

        if ca == cb and abs(ra - rb) == 1:
            top_r = min(ra, rb)
            sign = self.instance.v_constraints[top_r][ca]
            if sign != 0:
                if ra < rb:
                    return self.relation_holds(val_a, val_b, sign)
                return self.relation_holds(val_b, val_a, sign)

        return True

    def is_assignment_consistent(self, domains: Domains, cell: Cell, value: int) -> bool:
        if self.stats is not None:
            self.stats.consistency_checks += 1

        for peer in self.peers(cell):
            if len(domains[peer]) == 1 and value in domains[peer]:
                return False

        for other, sign in self.inequality_neighbors(cell):
            other_domain = domains[other]
            ok = any(self.relation_holds(value, ov, sign) for ov in other_domain)
            if not ok:
                return False

        return True

    def all_constraints_satisfied(self, domains: Domains) -> bool:
        if any(len(domains[cell]) != 1 for cell in self.cells):
            return False

        for r in range(self.n):
            row_vals = [next(iter(domains[(r, c)])) for c in range(self.n)]
            if len(set(row_vals)) != self.n:
                return False

        for c in range(self.n):
            col_vals = [next(iter(domains[(r, c)])) for r in range(self.n)]
            if len(set(col_vals)) != self.n:
                return False

        for r in range(self.n):
            for c in range(self.n - 1):
                sign = self.instance.h_constraints[r][c]
                if sign == 0:
                    continue
                lv = next(iter(domains[(r, c)]))
                rv = next(iter(domains[(r, c + 1)]))
                if not self.relation_holds(lv, rv, sign):
                    return False

        for r in range(self.n - 1):
            for c in range(self.n):
                sign = self.instance.v_constraints[r][c]
                if sign == 0:
                    continue
                tv = next(iter(domains[(r, c)]))
                bv = next(iter(domains[(r + 1, c)]))
                if not self.relation_holds(tv, bv, sign):
                    return False

        return True

    def has_empty_domain(self, domains: Domains) -> bool:
        return any(len(domains[cell]) == 0 for cell in self.cells)

    def copy_domains(self, domains: Domains) -> Domains:
        return {cell: set(vals) for cell, vals in domains.items()}

    def reduce_domains(self, domains: Domains) -> bool:
        queue = deque(self.cells)
        while queue:
            if self.stats is not None:
                self.stats.propagation_steps += 1
            cell = queue.popleft()
            current = set(domains[cell])
            reduced = {v for v in current if self.is_assignment_consistent(domains, cell, v)}
            if not reduced:
                return False
            if reduced != current:
                if self.stats is not None:
                    self.stats.domain_reductions += 1
                domains[cell] = reduced
                for peer in self.peers(cell):
                    queue.append(peer)
                for other, _ in self.inequality_neighbors(cell):
                    queue.append(other)
        return True

    def choose_unassigned_cell(self, domains: Domains) -> Optional[Cell]:
        candidates = [cell for cell in self.cells if len(domains[cell]) > 1]
        if not candidates:
            return None

        return min(
            candidates,
            key=lambda c: (len(domains[c]), -(len(self.peers(c)) + len(self.inequality_neighbors(c)))),
        )

    def to_grid(self, domains: Domains) -> List[List[int]]:
        return [[next(iter(domains[(r, c)])) for c in range(self.n)] for r in range(self.n)]

    def is_valid_instance(self) -> bool:
        domains = self.initial_domains()
        return self.reduce_domains(domains)


def domains_unassigned_count(domains: Domains) -> int:
    return sum(1 for vals in domains.values() if len(vals) > 1)


def domains_violation_lower_bound(csp: FutoshikiCSP, domains: Domains) -> int:
    # Lower bound on required assignments: each unassigned cell needs at least one assignment.
    return domains_unassigned_count(domains)
