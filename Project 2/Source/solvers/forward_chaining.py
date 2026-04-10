from Source.logic.kb import *
from typing import List, Tuple, Optional, Dict, Set
from Source.utils.parser import FutoshikiInstance
Clause = Tuple[str, ...]


def get_atom(literal):
    if literal.startswith('~'):
        return literal[1:], False
    return literal, True

def literal_value(literal: str, assignment: Dict[str, bool])->Optional[bool]:
    atom, positive = get_atom(literal)
    if atom not in assignment:
        return None
    return assignment[atom] if positive else not assignment[atom]

def clause_status(clause: Clause, assignment: Dict[str, bool]):
    last_unassigned = None
    has_true = False
    unassigned = 0
    for lit in clause:
        val = literal_value(lit, assignment)
        if val is True:
            has_true = True
            break
        if val is None:
            unassigned += 1
            last_unassigned = lit
    if has_true:
        return True, False, unassigned, last_unassigned
    if unassigned == 0:
        return False, True, 0, None
    return False, False, unassigned, last_unassigned

def unit_propagate(clauses: List[Clause], assignment: Dict[str,bool]) -> Optional[Dict[str,bool]]:
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            sat, conflict, unassigned, last_un = clause_status(clause, assignment)
            if conflict:
                return None
            if (not sat) and unassigned == 1:
                atom, positive = get_atom(last_un)
                val = True if positive else False
                if atom in assignment:
                    if assignment[atom] != val:
                        return None
                    continue
                assignment[atom] = val
                changed = True
                break
    return assignment

def choose_unassigned_atom(clauses: List[Clause], assignment: Dict[str, bool]) -> Optional[str]:
    for clause in clauses:
        for lit in clause:
            atom, _ = get_atom(lit)
            if atom not in assignment:
                return atom
    return None

def dpll(clauses: List[Clause], assignment: Dict[str,bool]) -> Optional[Dict[str,bool]]:
    assignment = dict(assignment)
    assignment = unit_propagate(clauses, assignment)
    if assignment is None:
        return None
    
    all_sat = True
    for clause in clauses:
        sat, conflict, _, _ = clause_status(clause, assignment)
        if conflict:
            return None
        if not sat:
            all_sat = False
    if all_sat:
        return assignment
    
    atom = choose_unassigned_atom(clauses, assignment)
    if atom is None:
        return None
    
    assignment_copy = dict(assignment)
    assignment_copy[atom] = True
    res = dpll(clauses, assignment_copy)
    if res is not None:
        return res
    
    assignment_copy = dict(assignment)
    assignment_copy[atom] = False
    res = dpll(clauses, assignment_copy)
    return res

def solve_dpll_instance(instance: FutoshikiInstance):
    kb = build_kb(instance)
    clauses = list(kb.clauses)
    clauses += [(f,) for f in kb.facts]
    model = dpll(clauses, {})
    if model is None:
        return None
    
    n = instance.n
    grid=[[0]*n for _ in range(n)]
    for atom, val in model.items():
        if not val:
            continue
        if atom.startswith("Val("):
            inner = atom[4:-1]
            i,j,v = [int(x) for x in inner.split(",")]
            grid[i-1][j-1] = v
    if any(0 in row for row in grid):
        return None
    return grid


def solve_fc(instance: FutoshikiInstance):
    return solve_dpll_instance(instance)