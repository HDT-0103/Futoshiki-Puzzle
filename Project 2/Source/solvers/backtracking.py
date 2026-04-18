from __future__ import annotations
from Source.utils.parser import FutoshikiInstance


def solve_bt(instance: FutoshikiInstance):
    """
    Backtracking solver.
    Returns solved grid (list[list[int]]) or None.
    """
    n = instance.n
    grid = [row[:] for row in instance.grid]
    h = instance.h_constraints       # List[List[int]]
    v = instance.v_constraints       # List[List[int]]

    empty = [(i, j) for i in range(n) for j in range(n) if grid[i][j] == 0]
    stats = {"inferences": 0, "expansions": 0}
    logs = []

    def valid(r, c, val):
        stats["inferences"] += 1
        # Row & column uniqueness
        for k in range(n):
            if k != c and grid[r][k] == val:
                return False
            if k != r and grid[k][c] == val:
                return False

        # Horizontal constraints
        if c > 0 and grid[r][c - 1] != 0:
            if h[r][c - 1] == 1 and not (grid[r][c - 1] < val):
                return False
            if h[r][c - 1] == -1 and not (grid[r][c - 1] > val):
                return False
        if c < n - 1 and grid[r][c + 1] != 0:
            if h[r][c] == 1 and not (val < grid[r][c + 1]):
                return False
            if h[r][c] == -1 and not (val > grid[r][c + 1]):
                return False

        # Vertical constraints
        if r > 0 and grid[r - 1][c] != 0:
            if v[r - 1][c] == 1 and not (grid[r - 1][c] < val):
                return False
            if v[r - 1][c] == -1 and not (grid[r - 1][c] > val):
                return False
        if r < n - 1 and grid[r + 1][c] != 0:
            if v[r][c] == 1 and not (val < grid[r + 1][c]):
                return False
            if v[r][c] == -1 and not (val > grid[r + 1][c]):
                return False

        return True

    def backtrack(idx):
        if idx == len(empty):
            return True
        stats["expansions"] += 1
        r, c = empty[idx]
        for val in range(1, n + 1):
            logs.append(f"Try ({r+1},{c+1}) = {val}")
            if valid(r, c, val):
                grid[r][c] = val
                logs.append(f"  SET ({r+1},{c+1}) = {val}")
                if backtrack(idx + 1):
                    return True
                grid[r][c] = 0
                logs.append(f"  UNDO ({r+1},{c+1})")
            else:
                logs.append(f"  FAIL ({r+1},{c+1}) = {val}")
        return False

    result_grid = [row[:] for row in grid] if backtrack(0) else None
    return result_grid, stats, logs