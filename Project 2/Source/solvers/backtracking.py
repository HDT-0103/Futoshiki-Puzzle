
from __future__ import annotations
from Source.utils.parser import FutoshikiInstance


def _int(tok: str) -> int:
    """Convert constraint token ('0', '1', '-1') to int."""
    return int(tok)


def solve_bt(instance: FutoshikiInstance):
    """
    Backtracking solver.
    Returns solved grid (list[list[int]]) or None.
    """
    n = instance.n
    grid = [row[:] for row in instance.grid]
    h = instance.h_constraints
    v = instance.v_constraints

    # Tìm các ô trống
    empty = [(i, j) for i in range(n) for j in range(n) if grid[i][j] == 0]

    def valid(r, c, val):
        # Row uniqueness
        for k in range(n):
            if k != c and grid[r][k] == val:
                return False
        # Column uniqueness
        for k in range(n):
            if k != r and grid[k][c] == val:
                return False

        # Horizontal: check constraint with left neighbor
        if c > 0 and grid[r][c - 1] != 0:
            hv = _int(h[r][c - 1])
            if hv == 1 and not (grid[r][c - 1] < val):    # left < right
                return False
            if hv == -1 and not (grid[r][c - 1] > val):    # left > right
                return False

        # Horizontal: check constraint with right neighbor
        if c < n - 1 and grid[r][c + 1] != 0:
            hv = _int(h[r][c])
            if hv == 1 and not (val < grid[r][c + 1]):     # left < right
                return False
            if hv == -1 and not (val > grid[r][c + 1]):     # left > right
                return False

        # Vertical: check constraint with top neighbor
        if r > 0 and grid[r - 1][c] != 0:
            vv = _int(v[r - 1][c])
            if vv == 1 and not (grid[r - 1][c] < val):     # top < bottom
                return False
            if vv == -1 and not (grid[r - 1][c] > val):    # top > bottom
                return False

        # Vertical: check constraint with bottom neighbor
        if r < n - 1 and grid[r + 1][c] != 0:
            vv = _int(v[r][c])
            if vv == 1 and not (val < grid[r + 1][c]):     # top < bottom
                return False
            if vv == -1 and not (val > grid[r + 1][c]):    # top > bottom
                return False

        return True

    def backtrack(idx):
        if idx == len(empty):
            return True

        r, c = empty[idx]
        for val in range(1, n + 1):
            if valid(r, c, val):
                grid[r][c] = val
                if backtrack(idx + 1):
                    return True
                grid[r][c] = 0
        return False

    if backtrack(0):
        return [row[:] for row in grid]
    return None


def solve_bf(instance: FutoshikiInstance):
    """
    Brute-force solver (thử tất cả hoán vị theo hàng).
    Chậm hơn backtracking nhiều, dùng để so sánh performance.
    Returns solved grid (list[list[int]]) or None.
    """
    from itertools import permutations

    n = instance.n
    grid = [row[:] for row in instance.grid]
    h = instance.h_constraints
    v = instance.v_constraints

    def check_constraints(g):
        """Check tất cả inequality constraints."""
        for i in range(n):
            for j in range(n - 1):
                hv = _int(h[i][j])
                if hv == 1 and not (g[i][j] < g[i][j + 1]):
                    return False
                if hv == -1 and not (g[i][j] > g[i][j + 1]):
                    return False
        for i in range(n - 1):
            for j in range(n):
                vv = _int(v[i][j])
                if vv == 1 and not (g[i][j] < g[i + 1][j]):
                    return False
                if vv == -1 and not (g[i][j] > g[i + 1][j]):
                    return False
        return True

    def check_cols(g, up_to):
        """Check column uniqueness lên đến hàng up_to."""
        for j in range(n):
            seen = set()
            for i in range(up_to + 1):
                if g[i][j] in seen:
                    return False
                seen.add(g[i][j])
        return True

    # Tạo các hoán vị hợp lệ cho mỗi hàng
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
            grid[row_idx] = perm[:]
            if check_cols(grid, row_idx):
                if solve_row(row_idx + 1):
                    return True
        grid[row_idx] = [0] * n
        return False

    if solve_row(0):
        return [row[:] for row in grid]
    return None