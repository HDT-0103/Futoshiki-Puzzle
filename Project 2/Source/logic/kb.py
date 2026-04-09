from __future__ import annotations

"""Knowledge Base generation utilities for Futoshiki."""

from dataclasses import dataclass
from typing import List, Tuple

from Source.utils.parser import FutoshikiInstance

Atom = str
Clause = Tuple[str, ...]


@dataclass(frozen=True)
class GroundKB:
    n: int
    facts: List[Atom]
    clauses: List[Clause]


def _val(i: int, j: int, v: int) -> Atom:
    return f"Val({i},{j},{v})"


def _given(i: int, j: int, v: int) -> Atom:
    return f"Given({i},{j},{v})"


def _less_h(i: int, j: int) -> Atom:
    return f"LessH({i},{j})"


def _greater_h(i: int, j: int) -> Atom:
    return f"GreaterH({i},{j})"


def _less_v(i: int, j: int) -> Atom:
    return f"LessV({i},{j})"


def _greater_v(i: int, j: int) -> Atom:
    return f"GreaterV({i},{j})"


def _less(v1: int, v2: int) -> Atom:
    return f"Less({v1},{v2})"


def _neg(atom: Atom) -> str:
    return f"~{atom}"


def _at_least_one_value_clauses(n: int) -> List[Clause]:
    clauses: List[Clause] = []
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            clauses.append(tuple(_val(i, j, v) for v in range(1, n + 1)))
    return clauses


def _at_most_one_value_clauses(n: int) -> List[Clause]:
    clauses: List[Clause] = []
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            for v1 in range(1, n + 1):
                for v2 in range(v1 + 1, n + 1):
                    clauses.append((_neg(_val(i, j, v1)), _neg(_val(i, j, v2))))
    return clauses


def _row_uniqueness_clauses(n: int) -> List[Clause]:
    clauses: List[Clause] = []
    for i in range(1, n + 1):
        for v in range(1, n + 1):
            for j1 in range(1, n + 1):
                for j2 in range(j1 + 1, n + 1):
                    clauses.append((_neg(_val(i, j1, v)), _neg(_val(i, j2, v))))
    return clauses


def _column_uniqueness_clauses(n: int) -> List[Clause]:
    clauses: List[Clause] = []
    for j in range(1, n + 1):
        for v in range(1, n + 1):
            for i1 in range(1, n + 1):
                for i2 in range(i1 + 1, n + 1):
                    clauses.append((_neg(_val(i1, j, v)), _neg(_val(i2, j, v))))
    return clauses


def _given_enforcement_clauses(instance: FutoshikiInstance) -> List[Clause]:
    clauses: List[Clause] = []
    for i in range(instance.n):
        for j in range(instance.n):
            v = instance.grid[i][j]
            if v != 0:
                clauses.append((_neg(_given(i + 1, j + 1, v)), _val(i + 1, j + 1, v)))
                clauses.append((_given(i + 1, j + 1, v),))
    return clauses


def _inequality_clauses(instance: FutoshikiInstance) -> List[Clause]:
    n = instance.n
    clauses: List[Clause] = []

    for i in range(1, n + 1):
        for j in range(1, n):
            sign = instance.h_constraints[i - 1][j - 1]
            if sign == 0:
                continue
            rel_atom = _less_h(i, j) if sign == 1 else _greater_h(i, j)
            clauses.append((rel_atom,))
            for v1 in range(1, n + 1):
                for v2 in range(1, n + 1):
                    ok = (v1 < v2) if sign == 1 else (v1 > v2)
                    if not ok:
                        clauses.append((_neg(rel_atom), _neg(_val(i, j, v1)), _neg(_val(i, j + 1, v2))))

    for i in range(1, n):
        for j in range(1, n + 1):
            sign = instance.v_constraints[i - 1][j - 1]
            if sign == 0:
                continue
            rel_atom = _less_v(i, j) if sign == 1 else _greater_v(i, j)
            clauses.append((rel_atom,))
            for v1 in range(1, n + 1):
                for v2 in range(1, n + 1):
                    ok = (v1 < v2) if sign == 1 else (v1 > v2)
                    if not ok:
                        clauses.append((_neg(rel_atom), _neg(_val(i, j, v1)), _neg(_val(i + 1, j, v2))))

    return clauses


def _arithmetic_facts(n: int) -> List[Atom]:
    facts: List[Atom] = []
    for v1 in range(1, n + 1):
        for v2 in range(1, n + 1):
            if v1 < v2:
                facts.append(_less(v1, v2))
    return facts


def build_kb(instance: FutoshikiInstance) -> GroundKB:
    n = instance.n
    facts: List[Atom] = []
    clauses: List[Clause] = []

    facts.extend(_arithmetic_facts(n))
    clauses.extend(_at_least_one_value_clauses(n))
    clauses.extend(_at_most_one_value_clauses(n))
    clauses.extend(_row_uniqueness_clauses(n))
    clauses.extend(_column_uniqueness_clauses(n))
    clauses.extend(_given_enforcement_clauses(instance))
    clauses.extend(_inequality_clauses(instance))

    return GroundKB(n=n, facts=facts, clauses=clauses)

