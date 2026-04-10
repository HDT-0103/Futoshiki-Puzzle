#!/usr/bin/env python3
"""
Futoshiki GUI v2 — with step-by-step solving animation.

Features:
- ▶ SOLVE: giải ra output ngay
- ▶ STEP-BY-STEP: animation từng bước, giảng viên quan sát được
- Speed slider: điều chỉnh tốc độ animation
- Hiển thị ô đang xét (vàng), ô đã giải (xanh), ô backtrack (đỏ flash)
"""

from __future__ import annotations

import os
import sys
import time
import threading
import tracemalloc
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from queue import Queue, Empty

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Source.utils.parser import parse_futoshiki_file, FutoshikiInstance

# ─────────────────────────────────────────────────────────────
# Solver registry
# ─────────────────────────────────────────────────────────────
SOLVERS = {}


def _register_solvers():
    try:
        from Source.solvers.backtracking import solve_bt
        SOLVERS["Backtracking"] = solve_bt
    except ImportError:
        pass
    try:
        from Source.solvers.forward_chaining import solve_fc
        SOLVERS["Forward Chaining"] = solve_fc
    except ImportError:
        pass
    try:
        from Source.solvers.backward_chaining import solve_bc
        SOLVERS["Backward Chaining"] = solve_bc
    except ImportError:
        pass
    try:
        from Source.solvers.astar import solve_astar
        SOLVERS["A* Search"] = solve_astar
    except ImportError:
        pass
    if not SOLVERS:
        SOLVERS["Backtracking (built-in)"] = _builtin_bt


def _builtin_bt(instance: FutoshikiInstance):
    n = instance.n
    grid = [row[:] for row in instance.grid]
    h, v = instance.h_constraints, instance.v_constraints
    empty = [(i, j) for i in range(n) for j in range(n) if grid[i][j] == 0]

    def ok(r, c, val):
        for k in range(n):
            if k != c and grid[r][k] == val: return False
            if k != r and grid[k][c] == val: return False
        if c > 0 and grid[r][c-1] != 0:
            if h[r][c-1] == 1 and not (grid[r][c-1] < val): return False
            if h[r][c-1] == -1 and not (grid[r][c-1] > val): return False
        if c < n-1 and grid[r][c+1] != 0:
            if h[r][c] == 1 and not (val < grid[r][c+1]): return False
            if h[r][c] == -1 and not (val > grid[r][c+1]): return False
        if r > 0 and grid[r-1][c] != 0:
            if v[r-1][c] == 1 and not (grid[r-1][c] < val): return False
            if v[r-1][c] == -1 and not (grid[r-1][c] > val): return False
        if r < n-1 and grid[r+1][c] != 0:
            if v[r][c] == 1 and not (val < grid[r+1][c]): return False
            if v[r][c] == -1 and not (val > grid[r+1][c]): return False
        return True

    def bt(idx):
        if idx == len(empty): return True
        r, c = empty[idx]
        for val in range(1, n+1):
            if ok(r, c, val):
                grid[r][c] = val
                if bt(idx+1): return True
                grid[r][c] = 0
        return False

    return [row[:] for row in grid] if bt(0) else None


def _step_by_step_bt(instance: FutoshikiInstance, step_queue: Queue, stop_flag: list):
    """
    Backtracking solver that sends each step to a queue for animation.
    
    Step types pushed to queue:
      ("try",    row, col, val)   — đang thử gán val cho (row,col)
      ("set",    row, col, val)   — gán thành công
      ("fail",   row, col, val)   — val không hợp lệ
      ("undo",   row, col)        — backtrack, xóa ô
      ("done",   grid)            — hoàn thành
      ("nosoln",)                 — không có lời giải
    """
    n = instance.n
    grid = [row[:] for row in instance.grid]
    h, v = instance.h_constraints, instance.v_constraints
    empty = [(i, j) for i in range(n) for j in range(n) if grid[i][j] == 0]

    def ok(r, c, val):
        for k in range(n):
            if k != c and grid[r][k] == val: return False
            if k != r and grid[k][c] == val: return False
        if c > 0 and grid[r][c-1] != 0:
            if h[r][c-1] == 1 and not (grid[r][c-1] < val): return False
            if h[r][c-1] == -1 and not (grid[r][c-1] > val): return False
        if c < n-1 and grid[r][c+1] != 0:
            if h[r][c] == 1 and not (val < grid[r][c+1]): return False
            if h[r][c] == -1 and not (val > grid[r][c+1]): return False
        if r > 0 and grid[r-1][c] != 0:
            if v[r-1][c] == 1 and not (grid[r-1][c] < val): return False
            if v[r-1][c] == -1 and not (grid[r-1][c] > val): return False
        if r < n-1 and grid[r+1][c] != 0:
            if v[r][c] == 1 and not (val < grid[r+1][c]): return False
            if v[r][c] == -1 and not (val > grid[r+1][c]): return False
        return True

    def bt(idx):
        if stop_flag[0]:
            return False
        if idx == len(empty):
            step_queue.put(("done", [row[:] for row in grid]))
            return True
        r, c = empty[idx]
        for val in range(1, n+1):
            if stop_flag[0]: return False
            step_queue.put(("try", r, c, val))
            if ok(r, c, val):
                grid[r][c] = val
                step_queue.put(("set", r, c, val))
                if bt(idx + 1):
                    return True
                grid[r][c] = 0
                step_queue.put(("undo", r, c))
            else:
                step_queue.put(("fail", r, c, val))
        return False

    if not bt(0) and not stop_flag[0]:
        step_queue.put(("nosoln",))


# ─────────────────────────────────────────────────────────────
# Colors
# ─────────────────────────────────────────────────────────────
C_BG         = "#0f1117"
C_PANEL      = "#1a1d2e"
C_CELL       = "#252840"
C_GIVEN      = "#3b2d66"
C_SOLVED     = "#1a4d38"
C_TRYING     = "#5a4a1a"     # vàng đậm — đang thử
C_FAIL       = "#5a1a1a"     # đỏ đậm — fail
C_NUM        = "#dddaf0"
C_GIVEN_NUM  = "#c9a6ff"
C_SOLVED_NUM = "#6fffaa"
C_TRY_NUM    = "#ffd866"     # vàng — số đang thử
C_SIGN       = "#ff5c5c"
C_LABEL      = "#8884a5"
C_TITLE      = "#ffffff"
C_ACCENT     = "#6e4fbf"
C_ACCENT_H   = "#8b6fe0"
C_GREEN      = "#27ae60"
C_GREEN_H    = "#2ecc71"
C_ORANGE     = "#e67e22"
C_ORANGE_H   = "#f39c12"
C_BORDER     = "#363a62"
C_ERR        = "#ff5c5c"
C_WARN       = "#f0a030"


# ─────────────────────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────────────────────
class FutoshikiGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Futoshiki Solver")
        self.root.configure(bg=C_BG)
        self.root.minsize(1060, 680)

        self.instance: FutoshikiInstance | None = None
        self.solution_grid: list[list[int]] | None = None
        self.current_path: Path | None = None

        # Step-by-step state
        self.anim_grid: list[list[int]] | None = None
        self.anim_highlight: dict = {}     # (row,col) -> color
        self.anim_running = False
        self.anim_stop = [False]
        self.step_queue: Queue | None = None
        self.step_count = 0

        self._build()
        _register_solvers()

    def _build(self):
        hdr = tk.Frame(self.root, bg=C_BG)
        hdr.pack(fill="x", padx=24, pady=(16, 4))
        tk.Label(hdr, text="FUTOSHIKI", font=("Consolas", 22, "bold"),
                 fg=C_TITLE, bg=C_BG).pack(side="left")
        tk.Label(hdr, text="Logic Puzzle Solver", font=("Consolas", 11),
                 fg=C_LABEL, bg=C_BG).pack(side="left", padx=(12, 0), pady=(6, 0))

        body = tk.Frame(self.root, bg=C_BG)
        body.pack(fill="both", expand=True, padx=24, pady=8)

        left = tk.Frame(body, bg=C_PANEL, width=250)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        self._build_left(left)

        mid = tk.Frame(body, bg=C_BG)
        mid.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(mid, bg=C_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self._draw())

        right = tk.Frame(body, bg=C_PANEL, width=230)
        right.pack(side="right", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        self._build_right(right)

        self.status = tk.StringVar(value="Load một file input để bắt đầu.")
        tk.Label(self.root, textvariable=self.status, font=("Consolas", 9),
                 fg=C_LABEL, bg=C_PANEL, anchor="w", padx=12, pady=4
                 ).pack(fill="x", side="bottom")

    def _build_left(self, p):
        tk.Label(p, text="CONTROLS", font=("Consolas", 10, "bold"),
                 fg=C_TITLE, bg=C_PANEL).pack(pady=(14, 8))

        tk.Label(p, text="Input file", font=("Consolas", 9),
                 fg=C_LABEL, bg=C_PANEL, anchor="w").pack(fill="x", padx=14)
        self.file_var = tk.StringVar(value="(chưa chọn)")
        tk.Label(p, textvariable=self.file_var, font=("Consolas", 9),
                 fg=C_ACCENT_H, bg=C_PANEL, anchor="w", wraplength=220
                 ).pack(fill="x", padx=14)
        self._btn(p, "Browse…", self._browse, C_ACCENT)

        ttk.Separator(p).pack(fill="x", padx=14, pady=8)

        tk.Label(p, text="Algorithm", font=("Consolas", 9),
                 fg=C_LABEL, bg=C_PANEL, anchor="w").pack(fill="x", padx=14)
        self.algo_var = tk.StringVar()
        self._algo_frame = tk.Frame(p, bg=C_PANEL)
        self._algo_frame.pack(fill="x", padx=14)
        self.root.after(100, self._rebuild_algo_radios)

        ttk.Separator(p).pack(fill="x", padx=14, pady=8)

        # Solve buttons
        self._btn(p, "▶  SOLVE", self._solve, C_GREEN)
        self.step_btn = self._btn(p, "⏩  STEP-BY-STEP", self._solve_step, C_ORANGE)
        self.stop_btn = self._btn(p, "⏹  STOP", self._stop_anim, C_ERR)

        ttk.Separator(p).pack(fill="x", padx=14, pady=8)

        # Speed control
        tk.Label(p, text="Animation speed", font=("Consolas", 9),
                 fg=C_LABEL, bg=C_PANEL, anchor="w").pack(fill="x", padx=14)

        speed_frame = tk.Frame(p, bg=C_PANEL)
        speed_frame.pack(fill="x", padx=14)
        tk.Label(speed_frame, text="Slow", font=("Consolas", 8),
                 fg=C_LABEL, bg=C_PANEL).pack(side="left")
        self.speed_var = tk.IntVar(value=85)
        tk.Scale(speed_frame, from_=0, to=100, orient="horizontal",
                 variable=self.speed_var, showvalue=False,
                 bg=C_PANEL, fg=C_NUM, troughcolor=C_CELL,
                 highlightthickness=0, length=120
                 ).pack(side="left", fill="x", expand=True, padx=4)
        tk.Label(speed_frame, text="Fast", font=("Consolas", 8),
                 fg=C_LABEL, bg=C_PANEL).pack(side="left")

        ttk.Separator(p).pack(fill="x", padx=14, pady=8)

        self._btn(p, "⟲  Reset", self._reset, C_ACCENT)
        self._btn(p, "💾  Save output", self._save, C_ACCENT)

    def _rebuild_algo_radios(self):
        for w in self._algo_frame.winfo_children():
            w.destroy()
        names = list(SOLVERS.keys()) if SOLVERS else ["(no solvers)"]
        self.algo_var.set(names[0])
        for name in names:
            tk.Radiobutton(
                self._algo_frame, text=name, variable=self.algo_var, value=name,
                font=("Consolas", 9), fg=C_NUM, bg=C_PANEL,
                selectcolor=C_CELL, activebackground=C_PANEL,
                activeforeground=C_NUM, anchor="w",
            ).pack(fill="x")

    def _build_right(self, p):
        tk.Label(p, text="STATISTICS", font=("Consolas", 10, "bold"),
                 fg=C_TITLE, bg=C_PANEL).pack(pady=(14, 8))

        self._stats = {}
        for key, label in [
            ("status",     "Status"),
            ("algorithm",  "Algorithm"),
            ("size",       "Grid size"),
            ("time",       "Time (s)"),
            ("memory",     "Peak mem (KB)"),
            ("expansions", "Steps"),
        ]:
            f = tk.Frame(p, bg=C_PANEL)
            f.pack(fill="x", padx=14, pady=3)
            tk.Label(f, text=label, font=("Consolas", 8), fg=C_LABEL, bg=C_PANEL,
                     anchor="w").pack(fill="x")
            lbl = tk.Label(f, text="—", font=("Consolas", 12, "bold"), fg=C_NUM,
                           bg=C_PANEL, anchor="w")
            lbl.pack(fill="x")
            self._stats[key] = lbl

        ttk.Separator(p).pack(fill="x", padx=14, pady=8)

        tk.Label(p, text="OUTPUT", font=("Consolas", 9, "bold"),
                 fg=C_TITLE, bg=C_PANEL).pack(padx=14, anchor="w")
        self.out_text = tk.Text(p, height=12, font=("Consolas", 8), fg=C_NUM,
                                bg=C_CELL, relief="flat", wrap="none", state="disabled")
        self.out_text.pack(fill="both", expand=True, padx=14, pady=(4, 14))

    def _btn(self, parent, text, cmd, color):
        b = tk.Button(parent, text=text, command=cmd,
                      font=("Consolas", 10, "bold"), fg="#fff", bg=color,
                      activebackground=color, activeforeground="#fff",
                      relief="flat", cursor="hand2", pady=5)
        b.pack(fill="x", padx=14, pady=3)
        orig = color
        lighter = {C_ACCENT: C_ACCENT_H, C_GREEN: C_GREEN_H,
                   C_ORANGE: C_ORANGE_H, C_ERR: "#ff7777"}.get(color, color)
        b.bind("<Enter>", lambda _: b.config(bg=lighter))
        b.bind("<Leave>", lambda _: b.config(bg=orig))
        return b

    # ── Stats ────────────────────────────────────────────────
    def _set_stat(self, key, val, color=None):
        lbl = self._stats.get(key)
        if lbl:
            lbl.config(text=str(val))
            if color: lbl.config(fg=color)

    def _clear_stats(self):
        for lbl in self._stats.values():
            lbl.config(text="—", fg=C_NUM)
        self.out_text.config(state="normal")
        self.out_text.delete("1.0", "end")
        self.out_text.config(state="disabled")

    # ── Grid drawing ─────────────────────────────────────────
    def _draw(self):
        c = self.canvas
        c.delete("all")

        if self.instance is None:
            c.create_text(c.winfo_width()//2, c.winfo_height()//2,
                          text="Load a puzzle to display",
                          font=("Consolas", 14), fill=C_LABEL)
            return

        n = self.instance.n
        # Determine which grid to show
        if self.anim_grid:
            show = self.anim_grid
        elif self.solution_grid:
            show = self.solution_grid
        else:
            show = self.instance.grid

        cw, ch = c.winfo_width(), c.winfo_height()
        gap = 24
        cell = min((cw - 40 - (n-1)*gap) / n,
                   (ch - 40 - (n-1)*gap) / n, 64)
        cell = max(cell, 28)

        gw = n*cell + (n-1)*gap
        gh = n*cell + (n-1)*gap
        ox = (cw - gw) / 2
        oy = (ch - gh) / 2

        for i in range(n):
            for j in range(n):
                x = ox + j*(cell+gap)
                y = oy + i*(cell+gap)
                val = show[i][j]
                given = self.instance.grid[i][j] != 0
                solved = (self.solution_grid is not None
                          and not given and val != 0)

                # Cell background — check animation highlight
                if (i, j) in self.anim_highlight:
                    bg = self.anim_highlight[(i, j)]
                elif given:
                    bg = C_GIVEN
                elif solved or (self.anim_grid and val != 0 and not given):
                    bg = C_SOLVED
                else:
                    bg = C_CELL

                c.create_rectangle(x, y, x+cell, y+cell,
                                   fill=bg, outline=C_BORDER, width=2)

                if val != 0:
                    if (i, j) in self.anim_highlight:
                        fg = C_TRY_NUM
                    elif given:
                        fg = C_GIVEN_NUM
                    elif solved or (self.anim_grid and not given):
                        fg = C_SOLVED_NUM
                    else:
                        fg = C_NUM
                    fs = max(int(cell*0.44), 12)
                    c.create_text(x+cell/2, y+cell/2,
                                  text=str(val), font=("Consolas", fs, "bold"), fill=fg)

                # Horizontal sign
                if j < n-1:
                    sign = self._h_sign(self.instance.h_constraints[i][j])
                    if sign:
                        c.create_text(x+cell+gap/2, y+cell/2, text=sign,
                                      font=("Consolas", max(int(gap*0.65), 13), "bold"),
                                      fill=C_SIGN)

                # Vertical sign
                if i < n-1:
                    sign = self._v_sign(self.instance.v_constraints[i][j])
                    if sign:
                        c.create_text(x+cell/2, y+cell+gap/2, text=sign,
                                      font=("Consolas", max(int(gap*0.65), 13), "bold"),
                                      fill=C_SIGN)

    @staticmethod
    def _h_sign(val) -> str | None:
        v = int(val) if not isinstance(val, int) else val
        if v == 1: return "<"
        if v == -1: return ">"
        return None

    @staticmethod
    def _v_sign(val) -> str | None:
        v = int(val) if not isinstance(val, int) else val
        if v == -1: return "∨"    # top > bottom
        if v == 1:  return "∧"    # top < bottom
        return None

    # ── Actions ──────────────────────────────────────────────
    def _browse(self):
        if self.anim_running:
            messagebox.showwarning("Busy", "Đang chạy animation, nhấn STOP trước!")
            return
        init_dir = _PROJECT_ROOT / "Inputs"
        if not init_dir.exists(): init_dir = _PROJECT_ROOT
        fp = filedialog.askopenfilename(
            title="Chọn file input", initialdir=str(init_dir),
            filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if not fp: return
        try:
            self.instance = parse_futoshiki_file(Path(fp))
            self.solution_grid = None
            self.anim_grid = None
            self.anim_highlight = {}
            self.current_path = Path(fp)
            self.file_var.set(Path(fp).name)
            self._clear_stats()
            self._set_stat("size", f"{self.instance.n} × {self.instance.n}")
            self._set_stat("status", "Loaded", C_NUM)
            self._draw()
            self.status.set(f"Loaded: {fp}")
        except Exception as e:
            messagebox.showerror("Parse error", str(e))

    # ── Instant solve ────────────────────────────────────────
    def _solve(self):
        if self.instance is None:
            messagebox.showwarning("No puzzle", "Chọn file input trước!")
            return
        if self.anim_running:
            messagebox.showwarning("Busy", "Đang chạy animation, nhấn STOP trước!")
            return

        algo_name = self.algo_var.get()
        solver_fn = SOLVERS.get(algo_name)
        if not solver_fn:
            messagebox.showerror("Error", f"Solver '{algo_name}' không tìm thấy.")
            return

        self.anim_grid = None
        self.anim_highlight = {}
        self._set_stat("status", "Solving…", C_WARN)
        self._set_stat("algorithm", algo_name)
        self.status.set(f"Đang giải bằng {algo_name}…")
        self.root.update()

        def run():
            try:
                tracemalloc.start()
                t0 = time.perf_counter()
                result = solver_fn(self.instance)
                elapsed = time.perf_counter() - t0
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                stats = {"time": round(elapsed, 4), "memory": round(peak/1024, 2)}

                if result is None:
                    self.root.after(0, self._on_no_solution)
                elif isinstance(result, list):
                    self.root.after(0, lambda: self._on_solved(result, stats))
                elif hasattr(result, "grid"):
                    self.root.after(0, lambda: self._on_solved(result.grid, stats))
                else:
                    self.root.after(0, lambda: self._on_solved(result, stats))
            except NotImplementedError as e:
                self.root.after(0, lambda: self._on_not_impl(str(e)))
            except Exception as e:
                self.root.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _on_solved(self, grid, stats):
        self.solution_grid = grid
        self._set_stat("status", "Solved ✓", C_SOLVED_NUM)
        self._set_stat("time", stats.get("time", "—"))
        self._set_stat("memory", stats.get("memory", "—"))
        self._set_stat("expansions", stats.get("expansions", "—"))
        self._draw()
        self._update_output_preview(grid)
        self.status.set(f"Solved in {stats.get('time', '?')}s")

    def _on_no_solution(self):
        self._set_stat("status", "No solution!", C_ERR)
        self.status.set("Không tìm được lời giải.")

    def _on_not_impl(self, msg):
        self._set_stat("status", "Not implemented", C_WARN)
        self.status.set(msg)
        messagebox.showinfo("Chưa implement", f"{msg}\n\nHãy implement solver tương ứng.")

    def _on_error(self, msg):
        self._set_stat("status", "Error!", C_ERR)
        self.status.set(f"Error: {msg}")
        messagebox.showerror("Solver error", msg)

    # ── Step-by-step solve ───────────────────────────────────
    def _solve_step(self):
        if self.instance is None:
            messagebox.showwarning("No puzzle", "Chọn file input trước!")
            return
        if self.anim_running:
            messagebox.showwarning("Busy", "Đang chạy animation rồi!")
            return

        self.anim_running = True
        self.anim_stop = [False]
        self.anim_grid = [row[:] for row in self.instance.grid]
        self.anim_highlight = {}
        self.solution_grid = None
        self.step_count = 0
        self.step_queue = Queue()

        self._set_stat("status", "Step-by-step…", C_WARN)
        self._set_stat("algorithm", "Backtracking (animated)")
        self._set_stat("expansions", "0")
        self.status.set("Animation đang chạy… Nhấn STOP để dừng.")

        # Run solver in background thread
        threading.Thread(
            target=_step_by_step_bt,
            args=(self.instance, self.step_queue, self.anim_stop),
            daemon=True
        ).start()

        # Start polling queue
        self._poll_steps()

    def _poll_steps(self):
        """Process steps from queue and update GUI."""
        if not self.anim_running:
            return

        # Calculate delay from speed slider (0=slow 500ms, 100=fast 1ms)
        speed = self.speed_var.get()
        delay = max(1, int(500 * (1 - speed / 100) ** 2))

        batch = 0
        max_batch = max(1, speed // 20)  # Process more steps at high speed

        while batch < max_batch:
            try:
                step = self.step_queue.get_nowait()
            except Empty:
                break

            batch += 1
            kind = step[0]

            if kind == "try":
                _, r, c, val = step
                self.step_count += 1
                self.anim_grid[r][c] = val
                self.anim_highlight = {(r, c): C_TRYING}
                self._set_stat("expansions", str(self.step_count))

            elif kind == "set":
                _, r, c, val = step
                self.anim_grid[r][c] = val
                self.anim_highlight = {(r, c): C_SOLVED}

            elif kind == "fail":
                _, r, c, val = step
                self.anim_grid[r][c] = 0
                self.anim_highlight = {(r, c): C_FAIL}

            elif kind == "undo":
                _, r, c = step
                self.anim_grid[r][c] = 0
                self.anim_highlight = {(r, c): C_FAIL}

            elif kind == "done":
                grid = step[1]
                self.solution_grid = grid
                self.anim_grid = None
                self.anim_highlight = {}
                self.anim_running = False
                self._set_stat("status", "Solved ✓", C_SOLVED_NUM)
                self._draw()
                self._update_output_preview(grid)
                self.status.set(f"Step-by-step hoàn tất! {self.step_count} steps.")
                return

            elif kind == "nosoln":
                self.anim_running = False
                self.anim_grid = None
                self.anim_highlight = {}
                self._set_stat("status", "No solution!", C_ERR)
                self._draw()
                self.status.set("Không tìm được lời giải.")
                return

        self._draw()
        self.root.after(delay, self._poll_steps)

    def _stop_anim(self):
        if self.anim_running:
            self.anim_stop[0] = True
            self.anim_running = False
            self.anim_grid = None
            self.anim_highlight = {}
            self._set_stat("status", "Stopped", C_WARN)
            self._draw()
            self.status.set("Animation đã dừng.")

    # ── Helpers ──────────────────────────────────────────────
    def _update_output_preview(self, grid):
        n = self.instance.n
        lines = []
        for i in range(n):
            parts = []
            for j in range(n):
                parts.append(str(grid[i][j]))
                if j < n-1:
                    s = self._h_sign(self.instance.h_constraints[i][j])
                    parts.append(s if s else " ")
            lines.append(" ".join(parts))
            if i < n-1:
                vp = []
                for j in range(n):
                    s = self._v_sign(self.instance.v_constraints[i][j])
                    vp.append(s if s else " ")
                lines.append("    ".join(vp))

        self.out_text.config(state="normal")
        self.out_text.delete("1.0", "end")
        self.out_text.insert("1.0", "\n".join(lines))
        self.out_text.config(state="disabled")

    def _reset(self):
        if self.anim_running:
            self._stop_anim()
        self.solution_grid = None
        self.anim_grid = None
        self.anim_highlight = {}
        self._clear_stats()
        if self.instance:
            self._set_stat("size", f"{self.instance.n} × {self.instance.n}")
            self._set_stat("status", "Loaded")
        self._draw()
        self.status.set("Reset.")

    def _save(self):
        if self.solution_grid is None:
            messagebox.showwarning("No solution", "Chưa có lời giải để lưu!")
            return
        init_dir = _PROJECT_ROOT / "Outputs"
        fp = filedialog.asksaveasfilename(
            title="Save output", initialdir=str(init_dir),
            defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not fp: return
        with open(fp, "w", encoding="utf-8") as f:
            for row in self.solution_grid:
                f.write(" ".join(str(v) for v in row) + "\n")
        self.status.set(f"Saved: {fp}")


def main():
    root = tk.Tk()
    root.geometry("1060x700")
    FutoshikiGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()