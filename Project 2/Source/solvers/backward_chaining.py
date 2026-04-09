"""
Backward Chaining (SLD Resolution) solver for Futoshiki.

Prolog-style interpreter:
- KB stores ground facts: Given(i,j,v), Val(i,j,v), Less(v1,v2), LessH(i,j), etc.
- Query Val(i,j,v) resolved by proving 4 sub-goals:
    1. Row uniqueness
    2. Column uniqueness
    3. Horizontal inequality constraints
    4. Vertical inequality constraints
- Assert/retract facts during depth-first search (SLD resolution).

FROM-SCRATCH implementation as required by the project.
"""

from __future__ import annotations
from Source.utils.parser import FutoshikiInstance


class KnowledgeBase:
    """Stores ground facts for backward chaining."""

    def __init__(self):
        self.facts: set[str] = set()

    def add(self, fact: str):
        self.facts.add(fact)

    def remove(self, fact: str):
        self.facts.discard(fact)

    def has(self, fact: str) -> bool:
        return fact in self.facts


class BackwardChainingEngine:
    """
    SLD-resolution backward chaining engine for Futoshiki.
    """

    def __init__(self, instance: FutoshikiInstance):
        self.n = instance.n
        self.grid = [row[:] for row in instance.grid]
        self.h = instance.h_constraints      # List[List[int]]
        self.v = instance.v_constraints      # List[List[int]]
        self.kb = KnowledgeBase()
        self.stats = {"expansions": 0, "inferences": 0}
        self._build_kb()

    def _build_kb(self):
        n = self.n

        # Facts: Given cells → Val(i,j,v)
        for i in range(n):
            for j in range(n):
                if self.grid[i][j] != 0:
                    v = self.grid[i][j]
                    self.kb.add(f"Given({i},{j},{v})")
                    self.kb.add(f"Val({i},{j},{v})")

        # Facts: Less(v1,v2) — background arithmetic
        for v1 in range(1, n + 1):
            for v2 in range(v1 + 1, n + 1):
                self.kb.add(f"Less({v1},{v2})")

        # Facts: Horizontal inequality constraints
        for i in range(n):
            for j in range(n - 1):
                if self.h[i][j] == 1:
                    self.kb.add(f"LessH({i},{j})")
                elif self.h[i][j] == -1:
                    self.kb.add(f"GreaterH({i},{j})")

        # Facts: Vertical inequality constraints
        for i in range(n - 1):
            for j in range(n):
                if self.v[i][j] == 1:
                    self.kb.add(f"LessV({i},{j})")
                elif self.v[i][j] == -1:
                    self.kb.add(f"GreaterV({i},{j})")

    # ── Sub-goal queries ─────────────────────────────────────

    def _not_in_row(self, row: int, val: int, skip_col: int) -> bool:
        """Prove: value `val` does not appear in `row` (except at `skip_col`)."""
        self.stats["inferences"] += 1
        for j in range(self.n):
            if j != skip_col and self.kb.has(f"Val({row},{j},{val})"):
                return False
        return True

    def _not_in_col(self, col: int, val: int, skip_row: int) -> bool:
        """Prove: value `val` does not appear in `col` (except at `skip_row`)."""
        self.stats["inferences"] += 1
        for i in range(self.n):
            if i != skip_row and self.kb.has(f"Val({i},{col},{val})"):
                return False
        return True

    def _h_ok(self, row: int, col: int, val: int) -> bool:
        """Prove: assigning `val` at (row,col) satisfies horizontal constraints."""
        self.stats["inferences"] += 1
        # Left neighbor
        if col > 0:
            left = self.grid[row][col - 1]
            if left != 0:
                if self.kb.has(f"LessH({row},{col-1})") and not self.kb.has(f"Less({left},{val})"):
                    return False
                if self.kb.has(f"GreaterH({row},{col-1})") and not self.kb.has(f"Less({val},{left})"):
                    return False
        # Right neighbor
        if col < self.n - 1:
            right = self.grid[row][col + 1]
            if right != 0:
                if self.kb.has(f"LessH({row},{col})") and not self.kb.has(f"Less({val},{right})"):
                    return False
                if self.kb.has(f"GreaterH({row},{col})") and not self.kb.has(f"Less({right},{val})"):
                    return False
        return True

    def _v_ok(self, row: int, col: int, val: int) -> bool:
        """Prove: assigning `val` at (row,col) satisfies vertical constraints."""
        self.stats["inferences"] += 1
        # Top neighbor
        if row > 0:
            top = self.grid[row - 1][col]
            if top != 0:
                if self.kb.has(f"LessV({row-1},{col})") and not self.kb.has(f"Less({top},{val})"):
                    return False
                if self.kb.has(f"GreaterV({row-1},{col})") and not self.kb.has(f"Less({val},{top})"):
                    return False
        # Bottom neighbor
        if row < self.n - 1:
            bot = self.grid[row + 1][col]
            if bot != 0:
                if self.kb.has(f"LessV({row},{col})") and not self.kb.has(f"Less({val},{bot})"):
                    return False
                if self.kb.has(f"GreaterV({row},{col})") and not self.kb.has(f"Less({bot},{val})"):
                    return False
        return True

    def _prove_val(self, row: int, col: int, val: int) -> bool:
        """
        Backward chaining query: can we prove Val(row, col, val)?
        
        Resolves 4 sub-goals:
          Val(i,j,v) :- not_in_row(i,v,j),
                        not_in_col(j,v,i),
                        h_ok(i,j,v),
                        v_ok(i,j,v).
        """
        self.stats["inferences"] += 1
        return (self._not_in_row(row, val, col)
                and self._not_in_col(col, val, row)
                and self._h_ok(row, col, val)
                and self._v_ok(row, col, val))

    # ── SLD Resolution search ────────────────────────────────

    def _resolve(self, idx: int, goals: list[tuple[int, int]]) -> bool:
        """
        Depth-first SLD resolution over empty cells.
        
        For each cell (goal), try values 1..N:
        - If _prove_val succeeds: ASSERT Val(i,j,v), recurse
        - If recursion fails: RETRACT Val(i,j,v), try next value
        """
        if idx == len(goals):
            return True

        row, col = goals[idx]
        self.stats["expansions"] += 1

        for val in range(1, self.n + 1):
            if self._prove_val(row, col, val):
                # Assert derived fact
                self.grid[row][col] = val
                self.kb.add(f"Val({row},{col},{val})")

                if self._resolve(idx + 1, goals):
                    return True

                # Retract on failure
                self.grid[row][col] = 0
                self.kb.remove(f"Val({row},{col},{val})")

        return False

    def solve(self) -> list[list[int]] | None:
        """Solve puzzle. Returns grid or None."""
        goals = [(i, j) for i in range(self.n) for j in range(self.n)
                 if self.grid[i][j] == 0]
        if self._resolve(0, goals):
            return [row[:] for row in self.grid]
        return None

    def get_stats(self) -> dict:
        return self.stats.copy()


# ── Public API ───────────────────────────────────────────────

def solve_bc(instance: FutoshikiInstance):
    """
    Backward Chaining solver entry point.
    Returns solved grid (list[list[int]]) or None.
    """
    engine = BackwardChainingEngine(instance)
    return engine.solve()