from Source.logic.kb import *

def get_atom(literal):
    if literal.startswith('~'):
        return literal[1:], False
    return literal, True

def is_literal_false(literal, known_facts):
    atom, is_positive = get_atom(literal)
    if is_positive:
        return f"~{atom}" in known_facts
    else:
        return atom in known_facts
def solve_forward_chaining(kb):
    known_facts = set(kb.facts)
    for clause in kb.clauses:
        if len(clause) == 1:
            known_facts.add(clause[0])
    
    agenda = list(known_facts)
    processed_facts = set()
    while agenda:
        p = agenda.pop(0)
        if p in processed_facts:
            continue
        processed_facts.add(p)

        for clause in kb.clauses:
            unfalsified_literals = []
            for literal in clause:
                if not is_literal_false(literal, known_facts):
                    unfalsified_literals.append(literal)

            if len(unfalsified_literals) == 1:
                new_fact = unfalsified_literals[0]
                if new_fact not in known_facts:
                    known_facts.add(new_fact)
                    agenda.append(new_fact)
            
            if len(unfalsified_literals) == 0:
                return None, "Contradiction found!"
            
    result = [f for f in known_facts if f.startswith("Val") and not f.startswith("~")]
    return result, "Success"
