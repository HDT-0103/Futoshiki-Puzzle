"""
Brute-force solver for Futoshiki.
Tries all row permutations, checks column uniqueness and constraints.
Slower than backtracking. Used as baseline for performance comparison.
"""

from __future__ import annotations
from itertools import permutations
from Source.utils.parser import FutoshikiInstance


def solve_bf(instance: FutoshikiInstance):
    """
    Brute-force solver.
    Returns solved grid (list[list[int]]) or None.
    """
    n = instance.n
    grid = [row[:] for row in instance.grid]
    h = instance.h_constraints
    v = instance.v_constraints

    stats = {"inferences": 0, "expansions": 0}
    logs = []

    def check_constraints(g):
        for i in range(n):
            for j in range(n - 1):
                stats["inferences"] += 1
                if h[i][j] == 1 and not (g[i][j] < g[i][j + 1]):
                    return False
                stats["inferences"] += 1
                if h[i][j] == -1 and not (g[i][j] > g[i][j + 1]):
                    return False
        for i in range(n - 1):
            for j in range(n):
                stats["inferences"] += 1
                if v[i][j] == 1 and not (g[i][j] < g[i + 1][j]):
                    return False
                stats["inferences"] += 1
                if v[i][j] == -1 and not (g[i][j] > g[i + 1][j]):
                    return False
        return True

    def check_cols(g, up_to):
        for j in range(n):
            seen = set()
            for i in range(up_to + 1):
                stats["inferences"] += 1
                if g[i][j] in seen:
                    return False
                seen.add(g[i][j])
        return True

    def row_perms(row_idx):
        fixed = {j: grid[row_idx][j] for j in range(n) if grid[row_idx][j] != 0}
        used = set(fixed.values())
        free = [j for j in range(n) if grid[row_idx][j] == 0]
        remain = [val for val in range(1, n + 1) if val not in used]
        results = []
        for p in permutations(remain):
            r = grid[row_idx][:]
            for k, j in enumerate(free):
                r[j] = p[k]
            results.append(r)
        return results

    all_perms = [row_perms(i) for i in range(n)]

    def solve_row(row_idx):
        if row_idx == n:
            return check_constraints(grid)
        for perm in all_perms[row_idx]:
            stats["expansions"] += 1
            grid[row_idx] = perm[:]
            logs.append(f"Try row {row_idx+1}: {perm}")
            if check_cols(grid, row_idx):
                logs.append(f"  Columns OK, go deeper")
                if solve_row(row_idx + 1):
                    return True
                logs.append(f"  Backtrack row {row_idx+1}")
            else:
                logs.append(f"  Column conflict at row {row_idx+1}")
        grid[row_idx] = [0] * n
        return False

    result_grid = [row[:] for row in grid] if solve_row(0) else None
    return result_grid, stats, logs