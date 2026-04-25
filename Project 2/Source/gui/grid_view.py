"""Puzzle grid rendering and domain calculation.

These are stateless drawing functions — they read from the given
`FutoshikiInstance` and `Domains` state and write to the canvas.
"""
from __future__ import annotations
import tkinter as tk

from Source.gui.theme import PALETTE as P, FONT


def h_sign(value: int) -> str | None:
    """Horizontal constraint symbol: 1 → '<', -1 → '>', 0 → None."""
    v = int(value) if not isinstance(value, int) else value
    return "<" if v == 1 else (">" if v == -1 else None)


def v_sign(value: int) -> str | None:
    """Vertical constraint symbol: 1 → '∧' (top<bottom), -1 → '∨' (top>bottom)."""
    v = int(value) if not isinstance(value, int) else value
    if v == 1:  return "\u2227"  # ∧
    if v == -1: return "\u2228"  # ∨
    return None


def compute_domain(inst, r: int, c: int, g: list[list[int]]) -> set[int]:
    """Return the set of values that could still be placed at (r, c)."""
    n = inst.n
    h = inst.h_constraints
    v = inst.v_constraints

    used = set()
    for k in range(n):
        if g[r][k]: used.add(g[r][k])
        if g[k][c]: used.add(g[k][c])

    out: set[int] = set()
    for vl in range(1, n+1):
        if vl in used: continue
        ok = True
        if c > 0 and g[r][c-1]:
            if h[r][c-1] == 1  and not g[r][c-1] < vl: ok = False
            if h[r][c-1] == -1 and not g[r][c-1] > vl: ok = False
        if c < n-1 and g[r][c+1]:
            if h[r][c] == 1  and not vl < g[r][c+1]: ok = False
            if h[r][c] == -1 and not vl > g[r][c+1]: ok = False
        if r > 0 and g[r-1][c]:
            if v[r-1][c] == 1  and not g[r-1][c] < vl: ok = False
            if v[r-1][c] == -1 and not g[r-1][c] > vl: ok = False
        if r < n-1 and g[r+1][c]:
            if v[r][c] == 1  and not vl < g[r+1][c]: ok = False
            if v[r][c] == -1 and not vl > g[r+1][c]: ok = False
        if ok: out.add(vl)
    return out


def draw_placeholder(canvas: tk.Canvas) -> None:
    """Welcome screen shown when no puzzle is loaded."""
    canvas.delete("all")
    cw, ch = canvas.winfo_width(), canvas.winfo_height()
    canvas.create_text(cw // 2, ch // 2 - 12,
                       text="FUTOSHIKI", font=(FONT, 30, "bold"),
                       fill=P["brd"])
    canvas.create_text(cw // 2, ch // 2 + 24,
                       text="Open a puzzle file to begin",
                       font=(FONT, 11), fill=P["lbl"])


def draw_grid(canvas: tk.Canvas, inst, *,
              sol: list[list[int]] | None,
              agrid: list[list[int]] | None,
              ahl: dict[tuple[int, int], str],
              effort: dict[tuple[int, int], int],
              show_heat: bool) -> None:
    """Render the puzzle grid with all overlays."""
    canvas.delete("all")

    if not inst:
        draw_placeholder(canvas)
        return

    n = inst.n
    show = agrid or sol or inst.grid
    cw, ch = canvas.winfo_width(), canvas.winfo_height()
    gap = 28
    sz = min((cw - 50 - (n - 1) * gap) / n,
             (ch - 50 - (n - 1) * gap) / n, 80)
    sz = max(sz, 30)
    gw = n * sz + (n - 1) * gap
    ox = (cw - gw) / 2
    oy = (ch - gw) / 2
    mx_e = max(effort.values()) if effort else 1

    for i in range(n):
        for j in range(n):
            _draw_cell(canvas, inst, show, i, j, ox, oy, sz, gap, n,
                       sol, agrid, ahl, effort, show_heat, mx_e)


def _draw_cell(canvas, inst, show, i, j, ox, oy, sz, gap, n,
               sol, agrid, ahl, effort, show_heat, mx_e):
    x, y = ox + j*(sz+gap), oy + i*(sz+gap)
    val = show[i][j]
    given = inst.grid[i][j] != 0
    is_sol = sol and not given and val != 0
    is_anim = agrid and not given and val != 0

    # Background
    if show_heat and (i, j) in effort:
        bg = P["heat"][min(int((effort[(i, j)] / mx_e) * 5), 5)]
    elif (i, j) in ahl:
        bg = ahl[(i, j)]
    elif given:
        bg = P["given"]
    elif is_sol or is_anim:
        bg = P["solved"]
    else:
        bg = P["cell"]

    # Rounded rectangle
    r = 6
    pts = [x+r, y, x+sz-r, y, x+sz, y, x+sz, y+r,
           x+sz, y+sz-r, x+sz, y+sz, x+sz-r, y+sz,
           x+r, y+sz, x, y+sz, x, y+sz-r, x, y+r, x, y]
    brd = P["brd_hi"] if (i, j) in ahl else P["brd"]
    canvas.create_polygon(pts, fill=bg, outline=brd, width=2, smooth=True)

    # Cell value or domain hint
    if val != 0:
        if (i, j) in ahl and ahl[(i, j)] == P["fail"]:
            fg = P["fnum"]
        elif (i, j) in ahl:
            fg = P["tnum"]
        elif given:
            fg = P["gnum"]
        elif is_sol or is_anim:
            fg = P["snum"]
        else:
            fg = P["num"]
        canvas.create_text(x + sz/2, y + sz/2, text=str(val),
                           font=(FONT, max(int(sz * .46), 14), "bold"),
                           fill=fg)
    elif not agrid and not sol:
        dom = compute_domain(inst, i, j, show)
        if dom and len(dom) < n:
            canvas.create_text(x + sz/2, y + sz/2,
                               text=" ".join(str(d) for d in sorted(dom)),
                               font=(FONT, max(int(sz * .16), 7)),
                               fill=P["domain"])

    # Constraint signs
    if j < n - 1:
        s = h_sign(inst.h_constraints[i][j])
        if s:
            canvas.create_text(x + sz + gap/2, y + sz/2, text=s,
                               font=(FONT, max(int(gap * .6), 14), "bold"),
                               fill=P["sign"])
    if i < n - 1:
        s = v_sign(inst.v_constraints[i][j])
        if s:
            canvas.create_text(x + sz/2, y + sz + gap/2, text=s,
                               font=(FONT, max(int(gap * .6), 14), "bold"),
                               fill=P["sign"])


def format_solution(inst, g: list[list[int]]) -> str:
    """Format a solved grid as plain text with inequality symbols."""
    n = inst.n
    lines = []
    for i in range(n):
        parts = []
        for j in range(n):
            parts.append(str(g[i][j]))
            if j < n - 1:
                s = h_sign(inst.h_constraints[i][j])
                parts.append(s if s else " ")
        lines.append(" ".join(parts))

        if i < n - 1:
            vp = []
            for j in range(n):
                s = v_sign(inst.v_constraints[i][j])
                vp.append(s if s else " ")
            lines.append("   ".join(vp))
    return "\n".join(lines)
