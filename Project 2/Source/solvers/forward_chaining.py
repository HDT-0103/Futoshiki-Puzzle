from Source.logic.kb import *
from typing import List, Tuple, Optional, Dict, Set
from Source.utils.parser import FutoshikiInstance
from collections import defaultdict
Clause = Tuple[str, ...]
import sys
sys.setrecursionlimit(5000) # Tăng giới hạn để xử lý lưới 9x9

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

#def unit_propagate(clauses: List[Clause], assignment: Dict[str,bool]) -> Optional[Dict[str,bool]]:
#    changed = True
#    while changed:
#        changed = False
#        for clause in clauses:
#            sat, conflict, unassigned, last_un = clause_status(clause, assignment)
#            if conflict:
#                return None
#            if (not sat) and unassigned == 1:
#                atom, positive = get_atom(last_un)
#                val = True if positive else False
#                if atom in assignment:
#                    if assignment[atom] != val:
#                        return None
#                    continue
#                assignment[atom] = val
#                changed = True
#                break
#    return assignment

def unit_propagate(
    clauses: List[Clause],
    assignment: Dict[str, bool],
    atom_to_clauses: Dict[str, List[Clause]] = None,
    stats: Dict[str, int] = None,
) -> Optional[Dict[str, bool]]:
    changed_atoms = list(assignment.keys())
    while changed_atoms:
        atom = changed_atoms.pop()
        relevant_clauses = atom_to_clauses.get(atom, clauses) if atom_to_clauses else clauses
        for clause in relevant_clauses:
            sat, conflict, unassigned, last_un = clause_status(clause, assignment)
            if conflict: return None
            if (not sat) and unassigned == 1:
                at, pos = get_atom(last_un)
                val = True if pos else False
                if at not in assignment:
                    assignment[at] = val
                    changed_atoms.append(at)
                    if stats is not None:
                        stats["inferences"] += 1
                elif assignment[at] != val: return None
    return assignment

def choose_unassigned_atom(clauses: List[Clause], assignment: Dict[str, bool]) -> Optional[str]:
    for clause in clauses:
        for lit in clause:
            atom, _ = get_atom(lit)
            if atom not in assignment:
                return atom
    return None

#def dpll(clauses: List[Clause], assignment: Dict[str,bool], steps: List[int], logs: list) -> Optional[Dict[str,bool]]:
#    steps[0] += 1
#    assignment = dict(assignment)
#    assignment = unit_propagate(clauses, assignment)
#    if assignment is None:
#        logs.append(f"Step {steps[0]}: Unit propagation -> conflict")
#        return None
    
#    all_sat = True
#    for clause in clauses:
#        sat, conflict, _, _ = clause_status(clause, assignment)
#        if conflict:
#            return None
#        if not sat:
#            all_sat = False
#    if all_sat:
#        return assignment
    
#    atom = choose_unassigned_atom(clauses, assignment)
#    if atom is None:
#        return None
    
#    logs.append(f"Step {steps[0]}: Branch on {atom} = True")
#    assignment_copy = dict(assignment)
#    assignment_copy[atom] = True
#    res = dpll(clauses, assignment_copy, steps, logs)
#    if res is not None:
#        return res
    
#    logs.append(f"Step {steps[0]}: Branch on {atom} = False")
#    assignment_copy = dict(assignment)
#    assignment_copy[atom] = False
#    res = dpll(clauses, assignment_copy, steps, logs)
#    return res

def dpll(
    clauses: List[Clause],
    assignment: Dict[str, bool],
    stats: Dict[str, int],
    logs: list,
    atom_to_clauses: dict = None,
) -> Optional[Dict[str, bool]]:
    stats["expansions"] += 1
    assignment = dict(assignment)
    
    # Lan truyền đơn vị
    assignment = unit_propagate(clauses, assignment, atom_to_clauses, stats)
    if assignment is None: return None
    
    # Chọn biến chưa gán
    atom = choose_unassigned_atom(clauses, assignment)
    if atom is None:
        # Kiểm tra conflict cuối cùng cho chắc chắn
        for c in clauses:
            _, conflict, _, _ = clause_status(c, assignment)
            if conflict: return None
        return assignment

    # Branching (truyền đủ steps, logs, index)
    for val in [True, False]:
        res = dpll(clauses, {**assignment, atom: val}, stats, logs, atom_to_clauses)
        if res is not None: return res
    return None

def solve_dpll_instance(instance: FutoshikiInstance):
    kb = build_kb(instance)
    clauses = list(kb.clauses)
    clauses += [(f,) for f in kb.facts]    

    # 1. TẠO INDEX ĐỂ TRÁNH TIMEOUT BÀI 9x9
    atom_to_clauses = defaultdict(list)
    for clause in clauses:
        for lit in clause:
            atom, _ = get_atom(lit)
            atom_to_clauses[atom].append(clause)

    initial_assignment = {}
    for clause in clauses:
        if len(clause) == 1:
            atom, pos = get_atom(clause[0])
            initial_assignment[atom] = pos

    stats = {"inferences": 0, "expansions": 0}
    logs = []
    logs.append(f"Initial facts: {len(initial_assignment)} atoms assigned")
    logs.append(f"Total clauses: {len(clauses)}")
    
    # 3. Chạy DPLL với initial_assignment thay vì {}
    model = dpll(clauses, initial_assignment, stats, logs, atom_to_clauses)

    if model is None:
        return None, stats, logs
        
    n = instance.n
    grid=[[0]*n for _ in range(n)]
    for atom, val in model.items():
        if not val: continue
        if atom.startswith("Val("):
            inner = atom[4:-1]
            i,j,v = [int(x) for x in inner.split(",")]
            grid[i-1][j-1] = v
            
    if any(0 in row for row in grid):
        return None, stats, logs
    return grid, stats, logs


def solve_fc(instance: FutoshikiInstance):
    return solve_dpll_instance(instance)