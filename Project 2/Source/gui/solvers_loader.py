"""Solver registry and animated backtracking fallback.

Each public solver is registered in `SOLVERS`. If a solver fails to
import, a trivial fallback is registered so the UI still works.
The animated backtracking is a separate instrumented implementation
used for step-by-step visualization (it posts progress events to a
queue instead of computing silently).
"""
from __future__ import annotations
import importlib
from queue import Queue
from typing import Callable


# Public registry populated by register_solvers()
SOLVERS: dict[str, Callable] = {}


def register_solvers() -> None:
    """Import all solver modules and register their entry functions."""
    modules = [
        ("Source.solvers.backtracking",      "Backtracking",      "solve_bt"),
        ("Source.solvers.bruteforce",        "Brute Force",       "solve_bf"),
        ("Source.solvers.forward_chaining",  "Forward Chaining",  "solve_fc"),
        ("Source.solvers.backward_chaining", "Backward Chaining", "solve_bc"),
        ("Source.solvers.astar",             "A* Search",         "solve_astar"),
    ]
    for mod_path, display_name, fn_name in modules:
        try:
            mod = importlib.import_module(mod_path)
            fn = getattr(mod, fn_name, None)
            if fn and not getattr(fn, "__is_stub__", False):
                SOLVERS[display_name] = fn
        except Exception:
            pass

    # Always provide at least one working solver
    if "Backtracking" not in SOLVERS:
        SOLVERS["Built-in BT"] = _fallback_solver


def _fallback_solver(inst):
    """Minimal backtracking solver — used when no external solver is found."""
    n = inst.n
    g = [r[:] for r in inst.grid]
    h, v = inst.h_constraints, inst.v_constraints
    empty = [(i, j) for i in range(n) for j in range(n) if g[i][j] == 0]

    def ok(r, c, vl):
        for k in range(n):
            if k != c and g[r][k] == vl: return False
            if k != r and g[k][c] == vl: return False
        if c > 0 and g[r][c-1]:
            if h[r][c-1] == 1  and not g[r][c-1] < vl: return False
            if h[r][c-1] == -1 and not g[r][c-1] > vl: return False
        if c < n-1 and g[r][c+1]:
            if h[r][c] == 1  and not vl < g[r][c+1]: return False
            if h[r][c] == -1 and not vl > g[r][c+1]: return False
        if r > 0 and g[r-1][c]:
            if v[r-1][c] == 1  and not g[r-1][c] < vl: return False
            if v[r-1][c] == -1 and not g[r-1][c] > vl: return False
        if r < n-1 and g[r+1][c]:
            if v[r][c] == 1  and not vl < g[r+1][c]: return False
            if v[r][c] == -1 and not vl > g[r+1][c]: return False
        return True

    def bt(idx):
        if idx == len(empty): return True
        r, c = empty[idx]
        for vl in range(1, n+1):
            if ok(r, c, vl):
                g[r][c] = vl
                if bt(idx+1): return True
                g[r][c] = 0
        return False

    return (g, {"inferences": 0, "expansions": 0}, []) if bt(0) else (None, {"inferences": 0, "expansions": 0}, [])


def animated_bt(inst, q: Queue, stop: list[bool]) -> None:
    """Backtracking instrumented to emit events for animation.

    Events posted to the queue:
      ("try",  r, c, val, effort_map)
      ("set",  r, c, val)
      ("fail", r, c, val)
      ("undo", r, c)
      ("done", grid, effort_map)
      ("nosoln",)
    """
    n = inst.n
    g = [r[:] for r in inst.grid]
    h, v = inst.h_constraints, inst.v_constraints
    empty = [(i, j) for i in range(n) for j in range(n) if g[i][j] == 0]
    effort: dict[tuple[int, int], int] = {}

    def ok(r, c, vl):
        for k in range(n):
            if k != c and g[r][k] == vl: return False
            if k != r and g[k][c] == vl: return False
        if c > 0 and g[r][c-1]:
            if h[r][c-1] == 1  and not g[r][c-1] < vl: return False
            if h[r][c-1] == -1 and not g[r][c-1] > vl: return False
        if c < n-1 and g[r][c+1]:
            if h[r][c] == 1  and not vl < g[r][c+1]: return False
            if h[r][c] == -1 and not vl > g[r][c+1]: return False
        if r > 0 and g[r-1][c]:
            if v[r-1][c] == 1  and not g[r-1][c] < vl: return False
            if v[r-1][c] == -1 and not g[r-1][c] > vl: return False
        if r < n-1 and g[r+1][c]:
            if v[r][c] == 1  and not vl < g[r+1][c]: return False
            if v[r][c] == -1 and not vl > g[r+1][c]: return False
        return True

    def bt(idx):
        if stop[0]: return False
        if idx == len(empty):
            q.put(("done", [row[:] for row in g], dict(effort))); return True
        r, c = empty[idx]
        effort[(r, c)] = effort.get((r, c), 0)
        for vl in range(1, n+1):
            if stop[0]: return False
            effort[(r, c)] += 1
            q.put(("try", r, c, vl, dict(effort)))
            if ok(r, c, vl):
                g[r][c] = vl
                q.put(("set", r, c, vl))
                if bt(idx+1): return True
                g[r][c] = 0
                q.put(("undo", r, c))
            else:
                q.put(("fail", r, c, vl))
        return False

    if not bt(0) and not stop[0]:
        q.put(("nosoln",))
