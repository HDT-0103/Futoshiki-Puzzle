"""
Backward Chaining (SLD Resolution) solver for Futoshiki.

Implements a Prolog-style backward chaining interpreter:
- Knowledge Base (KB) contains facts and Horn clause rules
- To solve: query Val(i, j, ?) for each empty cell
- Engine recursively resolves sub-goals via depth-first search

This is a FROM-SCRATCH implementation as required by the project.
"""

from __future__ import annotations
from Source.utils.parser import FutoshikiInstance


# ─────────────────────────────────────────────────────────────
# Knowledge Base
# ─────────────────────────────────────────────────────────────

class KnowledgeBase:
    """
    Stores facts and rules for backward chaining.
    
    Facts:  ground atoms like Given(1,1,2), LessH(1,1), Less(1,2), ...
    Rules:  Horn clauses  head :- body1, body2, ...
    """

    def __init__(self, n: int):
        self.n = n
        self.facts: set[str] = set()
        self.rules: list[tuple[str, list[str]]] = []  # (head_template, body_conditions)

    def add_fact(self, fact: str):
        self.facts.add(fact)

    def has_fact(self, fact: str) -> bool:
        return fact in self.facts

    def add_rule(self, head: str, body: list[str]):
        """Add a Horn clause: head :- body[0], body[1], ..."""
        self.rules.append((head, body))


# ─────────────────────────────────────────────────────────────
# Backward Chaining Engine
# ─────────────────────────────────────────────────────────────

class BackwardChainingEngine:
    """
    SLD-resolution style backward chaining engine.
    
    Giải Futoshiki bằng cách:
    1. Xây dựng KB từ puzzle instance (facts + rules)
    2. Với mỗi ô trống, query Val(i,j,v) cho v = 1..N
    3. Mỗi query được resolve bằng cách kiểm tra sub-goals:
       - Giá trị không trùng trong hàng (row uniqueness)
       - Giá trị không trùng trong cột (column uniqueness)
       - Thỏa mãn tất cả inequality constraints liên quan
    4. Khi gán thành công, thêm fact Val(i,j,v) vào KB
       để các query tiếp theo sử dụng
    """

    def __init__(self, instance: FutoshikiInstance):
        self.instance = instance
        self.n = instance.n
        self.grid = [row[:] for row in instance.grid]
        self.kb = KnowledgeBase(self.n)
        self.stats = {"expansions": 0, "inferences": 0}

        self._build_kb()

    def _build_kb(self):
        """Xây dựng Knowledge Base từ puzzle instance."""
        n = self.n
        inst = self.instance

        # ── Fact: Given(i, j, v) ──
        for i in range(n):
            for j in range(n):
                if inst.grid[i][j] != 0:
                    v = inst.grid[i][j]
                    self.kb.add_fact(f"Given({i},{j},{v})")
                    self.kb.add_fact(f"Val({i},{j},{v})")

        # ── Fact: Less(v1, v2) — background arithmetic ──
        for v1 in range(1, n + 1):
            for v2 in range(1, n + 1):
                if v1 < v2:
                    self.kb.add_fact(f"Less({v1},{v2})")

        # ── Fact: Inequality constraints from puzzle ──
        for i in range(n):
            for j in range(n - 1):
                tok = int(inst.h_constraints[i][j])
                if tok == 1:
                    self.kb.add_fact(f"LessH({i},{j})")      # cell(i,j) < cell(i,j+1)
                elif tok == -1:
                    self.kb.add_fact(f"GreaterH({i},{j})")    # cell(i,j) > cell(i,j+1)

        for i in range(n - 1):
            for j in range(n):
                tok = int(inst.v_constraints[i][j])
                if tok == 1:
                    self.kb.add_fact(f"LessV({i},{j})")       # cell(i,j) < cell(i+1,j)
                elif tok == -1:
                    self.kb.add_fact(f"GreaterV({i},{j})")    # cell(i,j) > cell(i+1,j)

    # ── Sub-goal resolution ──────────────────────────────────

    def _query_not_in_row(self, row: int, val: int, exclude_col: int) -> bool:
        """
        Sub-goal: giá trị val chưa xuất hiện trong hàng row
        (ngoại trừ vị trí exclude_col).
        
        Backward chaining: kiểm tra ∀j ≠ exclude_col: ¬Val(row, j, val)
        """
        self.stats["inferences"] += 1
        for j in range(self.n):
            if j != exclude_col and self.kb.has_fact(f"Val({row},{j},{val})"):
                return False
        return True

    def _query_not_in_col(self, col: int, val: int, exclude_row: int) -> bool:
        """
        Sub-goal: giá trị val chưa xuất hiện trong cột col
        (ngoại trừ vị trí exclude_row).
        """
        self.stats["inferences"] += 1
        for i in range(self.n):
            if i != exclude_row and self.kb.has_fact(f"Val({i},{col},{val})"):
                return False
        return True

    def _query_h_constraint(self, row: int, col: int, val: int) -> bool:
        """
        Sub-goal: kiểm tra tất cả horizontal constraints liên quan đến (row, col).
        
        Rule (backward):
          Val(row, col, val) is consistent with LessH/GreaterH
          ← check left neighbor: LessH(row, col-1) → need Less(neighbor_val, val)
          ← check right neighbor: LessH(row, col) → need Less(val, neighbor_val)
          (tương tự cho GreaterH)
        """
        self.stats["inferences"] += 1

        # Check constraint with LEFT neighbor (col-1, col)
        if col > 0:
            left_val = self.grid[row][col - 1]
            if left_val != 0:
                # LessH(row, col-1): left < right → Less(left_val, val)
                if self.kb.has_fact(f"LessH({row},{col-1})"):
                    if not self.kb.has_fact(f"Less({left_val},{val})"):
                        return False
                # GreaterH(row, col-1): left > right → Less(val, left_val)
                if self.kb.has_fact(f"GreaterH({row},{col-1})"):
                    if not self.kb.has_fact(f"Less({val},{left_val})"):
                        return False

        # Check constraint with RIGHT neighbor (col, col+1)
        if col < self.n - 1:
            right_val = self.grid[row][col + 1]
            if right_val != 0:
                # LessH(row, col): this < right → Less(val, right_val)
                if self.kb.has_fact(f"LessH({row},{col})"):
                    if not self.kb.has_fact(f"Less({val},{right_val})"):
                        return False
                # GreaterH(row, col): this > right → Less(right_val, val)
                if self.kb.has_fact(f"GreaterH({row},{col})"):
                    if not self.kb.has_fact(f"Less({right_val},{val})"):
                        return False

        return True

    def _query_v_constraint(self, row: int, col: int, val: int) -> bool:
        """
        Sub-goal: kiểm tra tất cả vertical constraints liên quan đến (row, col).
        """
        self.stats["inferences"] += 1

        # Check constraint with TOP neighbor (row-1, row)
        if row > 0:
            top_val = self.grid[row - 1][col]
            if top_val != 0:
                # LessV(row-1, col): top < bottom → Less(top_val, val)
                if self.kb.has_fact(f"LessV({row-1},{col})"):
                    if not self.kb.has_fact(f"Less({top_val},{val})"):
                        return False
                # GreaterV(row-1, col): top > bottom → Less(val, top_val)
                if self.kb.has_fact(f"GreaterV({row-1},{col})"):
                    if not self.kb.has_fact(f"Less({val},{top_val})"):
                        return False

        # Check constraint with BOTTOM neighbor (row, row+1)
        if row < self.n - 1:
            bot_val = self.grid[row + 1][col]
            if bot_val != 0:
                # LessV(row, col): this < bottom → Less(val, bot_val)
                if self.kb.has_fact(f"LessV({row},{col})"):
                    if not self.kb.has_fact(f"Less({val},{bot_val})"):
                        return False
                # GreaterV(row, col): this > bottom → Less(bot_val, val)
                if self.kb.has_fact(f"GreaterV({row},{col})"):
                    if not self.kb.has_fact(f"Less({bot_val},{val})"):
                        return False

        return True

    def _query_val(self, row: int, col: int, val: int) -> bool:
        """
        Main backward chaining query:
        
        Can we prove Val(row, col, val)?
        
        Rule:
          Val(i, j, v) :-
              not_in_row(i, v, j),      ← v không trùng trong hàng
              not_in_col(j, v, i),      ← v không trùng trong cột
              h_constraint_ok(i, j, v), ← thỏa inequality ngang
              v_constraint_ok(i, j, v). ← thỏa inequality dọc
        
        Resolve each sub-goal via backward chaining.
        """
        self.stats["inferences"] += 1

        # Sub-goal 1: Row uniqueness
        if not self._query_not_in_row(row, val, col):
            return False

        # Sub-goal 2: Column uniqueness
        if not self._query_not_in_col(col, val, row):
            return False

        # Sub-goal 3: Horizontal inequality constraints
        if not self._query_h_constraint(row, col, val):
            return False

        # Sub-goal 4: Vertical inequality constraints
        if not self._query_v_constraint(row, col, val):
            return False

        return True

    # ── Main solve loop ──────────────────────────────────────

    def _solve_cell(self, cell_idx: int, empty_cells: list[tuple[int, int]]) -> bool:
        """
        SLD Resolution: attempt to prove Val(i, j, v) for the next empty cell.
        
        Depth-first search over possible values (like Prolog's search strategy):
        - For each candidate value v in 1..N:
            - Query: can we prove Val(i, j, v)?
            - If yes: assert Val(i, j, v) as new fact, recurse to next cell
            - If subsequent cells fail: retract Val(i, j, v), try next v
        """
        if cell_idx == len(empty_cells):
            return True  # All cells resolved

        row, col = empty_cells[cell_idx]
        self.stats["expansions"] += 1

        for val in range(1, self.n + 1):
            # Backward chaining: try to prove Val(row, col, val)
            if self._query_val(row, col, val):
                # Assert the derived fact
                self.grid[row][col] = val
                self.kb.add_fact(f"Val({row},{col},{val})")

                # Recurse: try to resolve remaining cells
                if self._solve_cell(cell_idx + 1, empty_cells):
                    return True

                # Retract: backtrack (remove the derived fact)
                self.grid[row][col] = 0
                self.kb.facts.discard(f"Val({row},{col},{val})")

        return False

    def solve(self) -> list[list[int]] | None:
        """
        Solve the Futoshiki puzzle using backward chaining.
        
        Returns solved grid or None.
        """
        # Collect empty cells (goals to resolve)
        empty_cells = [
            (i, j)
            for i in range(self.n)
            for j in range(self.n)
            if self.grid[i][j] == 0
        ]

        if self._solve_cell(0, empty_cells):
            return [row[:] for row in self.grid]
        return None

    def get_stats(self) -> dict:
        return self.stats.copy()


# ─────────────────────────────────────────────────────────────
# Public API (matches project interface)
# ─────────────────────────────────────────────────────────────

def solve_bc(instance: FutoshikiInstance):
    """
    Backward Chaining solver — entry point.
    
    Args:
        instance: FutoshikiInstance from parser
        
    Returns:
        list[list[int]]: solved grid, or None if no solution
    """
    engine = BackwardChainingEngine(instance)
    return engine.solve()