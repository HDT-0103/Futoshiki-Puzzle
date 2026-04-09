
from __future__ import annotations

import os
import sys
import time
import threading
import tracemalloc
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# ── Fix import path ──────────────────────────────────────────
# Cho phép chạy cả `python -m Source.gui` lẫn `python Source/gui.py`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Source.utils.parser import parse_futoshiki_file, FutoshikiInstance


# ─────────────────────────────────────────────────────────────
# Solver registry — mỗi solver là 1 hàm solve_xxx(instance) -> grid
# Khi teammate implement xong solver nào, bỏ comment dòng tương ứng
# ─────────────────────────────────────────────────────────────
SOLVERS = {}


def _register_solvers():
    """
    Đăng ký các solver có sẵn.
    Nếu solver chưa implement (raise NotImplementedError), vẫn đăng ký
    nhưng GUI sẽ bắt lỗi khi chạy.
    """
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

    # Nếu chưa có solver nào hoạt động, thêm backtracking built-in để test GUI
    if not SOLVERS:
        SOLVERS["Backtracking (built-in)"] = _builtin_backtracking


def _builtin_backtracking(instance: FutoshikiInstance):
    """
    Backtracking solver tối giản — dùng để test GUI khi chưa có solver nào.
    Trả về grid (list[list[int]]) hoặc None.
    """
    n = instance.n
    grid = [row[:] for row in instance.grid]
    h = instance.h_constraints
    v = instance.v_constraints

    empty = [(i, j) for i in range(n) for j in range(n) if grid[i][j] == 0]

    def _int(tok):
        return int(tok)

    def valid(r, c, val):
        for k in range(n):
            if k != c and grid[r][k] == val:
                return False
            if k != r and grid[k][c] == val:
                return False
        if c > 0 and grid[r][c - 1] != 0:
            hv = _int(h[r][c - 1])
            if hv == 1 and not (grid[r][c - 1] < val):
                return False
            if hv == -1 and not (grid[r][c - 1] > val):
                return False
        if c < n - 1 and grid[r][c + 1] != 0:
            hv = _int(h[r][c])
            if hv == 1 and not (val < grid[r][c + 1]):
                return False
            if hv == -1 and not (val > grid[r][c + 1]):
                return False
        if r > 0 and grid[r - 1][c] != 0:
            vv = _int(v[r - 1][c])
            if vv == 1 and not (grid[r - 1][c] < val):
                return False
            if vv == -1 and not (grid[r - 1][c] > val):
                return False
        if r < n - 1 and grid[r + 1][c] != 0:
            vv = _int(v[r][c])
            if vv == 1 and not (val < grid[r + 1][c]):
                return False
            if vv == -1 and not (val > grid[r + 1][c]):
                return False
        return True

    def bt(idx):
        if idx == len(empty):
            return True
        r, c = empty[idx]
        for val in range(1, n + 1):
            if valid(r, c, val):
                grid[r][c] = val
                if bt(idx + 1):
                    return True
                grid[r][c] = 0
        return False

    return [row[:] for row in grid] if bt(0) else None


# ─────────────────────────────────────────────────────────────
# Color scheme
# ─────────────────────────────────────────────────────────────
C_BG         = "#0f1117"
C_PANEL      = "#1a1d2e"
C_CELL       = "#252840"
C_GIVEN      = "#3b2d66"
C_SOLVED     = "#1a4d38"
C_NUM        = "#dddaf0"
C_GIVEN_NUM  = "#c9a6ff"
C_SOLVED_NUM = "#6fffaa"
C_SIGN       = "#ff5c5c"
C_LABEL      = "#8884a5"
C_TITLE      = "#ffffff"
C_ACCENT     = "#6e4fbf"
C_ACCENT_H   = "#8b6fe0"
C_GREEN      = "#27ae60"
C_GREEN_H    = "#2ecc71"
C_BORDER     = "#363a62"
C_ERR        = "#ff5c5c"
C_WARN       = "#f0a030"


# ─────────────────────────────────────────────────────────────
# Main GUI class
# ─────────────────────────────────────────────────────────────
class FutoshikiGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Futoshiki Solver")
        self.root.configure(bg=C_BG)
        self.root.minsize(960, 640)

        self.instance: FutoshikiInstance | None = None
        self.solution_grid: list[list[int]] | None = None
        self.current_path: Path | None = None

        self._build()
        _register_solvers()

    # ── Build UI ─────────────────────────────────────────────
    def _build(self):
        # Title
        hdr = tk.Frame(self.root, bg=C_BG)
        hdr.pack(fill="x", padx=24, pady=(16, 4))
        tk.Label(hdr, text="FUTOSHIKI", font=("Consolas", 22, "bold"),
                 fg=C_TITLE, bg=C_BG).pack(side="left")
        tk.Label(hdr, text="Logic Puzzle Solver", font=("Consolas", 11),
                 fg=C_LABEL, bg=C_BG).pack(side="left", padx=(12, 0), pady=(6, 0))

        body = tk.Frame(self.root, bg=C_BG)
        body.pack(fill="both", expand=True, padx=24, pady=8)

        # Left panel
        left = tk.Frame(body, bg=C_PANEL, width=230)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        self._build_left(left)

        # Center canvas
        mid = tk.Frame(body, bg=C_BG)
        mid.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(mid, bg=C_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self._draw())

        # Right panel
        right = tk.Frame(body, bg=C_PANEL, width=230)
        right.pack(side="right", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        self._build_right(right)

        # Status bar
        self.status = tk.StringVar(value="Load một file input để bắt đầu.")
        tk.Label(self.root, textvariable=self.status, font=("Consolas", 9),
                 fg=C_LABEL, bg=C_PANEL, anchor="w", padx=12, pady=4
                 ).pack(fill="x", side="bottom")

    def _build_left(self, p):
        tk.Label(p, text="CONTROLS", font=("Consolas", 10, "bold"),
                 fg=C_TITLE, bg=C_PANEL).pack(pady=(14, 8))

        # File
        tk.Label(p, text="Input file", font=("Consolas", 9),
                 fg=C_LABEL, bg=C_PANEL, anchor="w").pack(fill="x", padx=14)
        self.file_var = tk.StringVar(value="(chưa chọn)")
        tk.Label(p, textvariable=self.file_var, font=("Consolas", 9),
                 fg=C_ACCENT_H, bg=C_PANEL, anchor="w", wraplength=200
                 ).pack(fill="x", padx=14)
        self._btn(p, "Browse…", self._browse, C_ACCENT)

        ttk.Separator(p).pack(fill="x", padx=14, pady=10)

        # Algorithm
        tk.Label(p, text="Algorithm", font=("Consolas", 9),
                 fg=C_LABEL, bg=C_PANEL, anchor="w").pack(fill="x", padx=14)
        self.algo_var = tk.StringVar()
        self._algo_frame = tk.Frame(p, bg=C_PANEL)
        self._algo_frame.pack(fill="x", padx=14)
        self.root.after(100, self._rebuild_algo_radios)

        ttk.Separator(p).pack(fill="x", padx=14, pady=10)

        # Buttons
        self._btn(p, "▶  SOLVE", self._solve, C_GREEN)
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
            ("expansions", "Nodes / steps"),
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
        b.pack(fill="x", padx=14, pady=4)
        lighter = C_ACCENT_H if color == C_ACCENT else C_GREEN_H
        b.bind("<Enter>", lambda _: b.config(bg=lighter))
        b.bind("<Leave>", lambda _: b.config(bg=color))
        return b

    # ── Stat helpers ─────────────────────────────────────────
    def _set_stat(self, key, val, color=None):
        lbl = self._stats.get(key)
        if lbl:
            lbl.config(text=str(val))
            if color:
                lbl.config(fg=color)

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
            c.create_text(c.winfo_width() // 2, c.winfo_height() // 2,
                          text="Load a puzzle to display",
                          font=("Consolas", 14), fill=C_LABEL)
            return

        n = self.instance.n
        show = self.solution_grid if self.solution_grid else self.instance.grid

        cw, ch = c.winfo_width(), c.winfo_height()
        gap = 24
        max_cell = 64
        cell = min((cw - 40 - (n - 1) * gap) / n,
                   (ch - 40 - (n - 1) * gap) / n,
                   max_cell)
        cell = max(cell, 28)

        gw = n * cell + (n - 1) * gap
        gh = n * cell + (n - 1) * gap
        ox = (cw - gw) / 2
        oy = (ch - gh) / 2

        for i in range(n):
            for j in range(n):
                x = ox + j * (cell + gap)
                y = oy + i * (cell + gap)
                val = show[i][j]
                given = self.instance.grid[i][j] != 0
                solved = (self.solution_grid is not None
                          and not given and val != 0)

                bg = C_GIVEN if given else (C_SOLVED if solved else C_CELL)
                c.create_rectangle(x, y, x + cell, y + cell,
                                   fill=bg, outline=C_BORDER, width=2)

                if val != 0:
                    fg = C_GIVEN_NUM if given else (C_SOLVED_NUM if solved else C_NUM)
                    fs = max(int(cell * 0.44), 12)
                    c.create_text(x + cell / 2, y + cell / 2,
                                  text=str(val), font=("Consolas", fs, "bold"), fill=fg)

                # Horizontal sign
                if j < n - 1:
                    sign = self._h_sign(self.instance.h_constraints[i][j])
                    if sign:
                        c.create_text(x + cell + gap / 2, y + cell / 2,
                                      text=sign,
                                      font=("Consolas", max(int(gap * 0.65), 13), "bold"),
                                      fill=C_SIGN)

                # Vertical sign
                if i < n - 1:
                    sign = self._v_sign(self.instance.v_constraints[i][j])
                    if sign:
                        c.create_text(x + cell / 2, y + cell + gap / 2,
                                      text=sign,
                                      font=("Consolas", max(int(gap * 0.65), 13), "bold"),
                                      fill=C_SIGN)

    @staticmethod
    def _h_sign(tok: str) -> str | None:
        if tok in ("1", "<"):
            return "<"
        if tok in ("-1", ">"):
            return ">"
        return None

    @staticmethod
    def _v_sign(tok: str) -> str | None:
        # Theo Figure 1 đề bài:
        # -1 = top > bottom → "∨" (mũi xuống, chỉ về phía giá trị nhỏ hơn)
        # 1  = top < bottom → "∧" (mũi lên, chỉ về phía giá trị nhỏ hơn)
        if tok in ("-1", ">"):
            return "∨"
        if tok in ("1", "<"):
            return "∧"
        return None

    # ── Actions ──────────────────────────────────────────────
    def _browse(self):
        init_dir = _PROJECT_ROOT / "Inputs"
        if not init_dir.exists():
            init_dir = _PROJECT_ROOT
        fp = filedialog.askopenfilename(
            title="Chọn file input Futoshiki",
            initialdir=str(init_dir),
            filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if not fp:
            return
        try:
            self.instance = parse_futoshiki_file(Path(fp))
            self.solution_grid = None
            self.current_path = Path(fp)
            self.file_var.set(Path(fp).name)
            self._clear_stats()
            self._set_stat("size", f"{self.instance.n} × {self.instance.n}")
            self._set_stat("status", "Loaded", C_NUM)
            self._draw()
            self.status.set(f"Loaded: {fp}")
        except Exception as e:
            messagebox.showerror("Parse error", str(e))

    def _solve(self):
        if self.instance is None:
            messagebox.showwarning("No puzzle", "Chọn file input trước!")
            return

        algo_name = self.algo_var.get()
        solver_fn = SOLVERS.get(algo_name)
        if solver_fn is None:
            messagebox.showerror("Error", f"Solver '{algo_name}' không tìm thấy.")
            return

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

                stats = {"time": round(elapsed, 4), "memory": round(peak / 1024, 2)}

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

        # Build output preview
        n = self.instance.n
        lines = []
        for i in range(n):
            parts = []
            for j in range(n):
                parts.append(str(grid[i][j]))
                if j < n - 1:
                    s = self._h_sign(self.instance.h_constraints[i][j])
                    parts.append(s if s else " ")
            lines.append(" ".join(parts))
            if i < n - 1:
                vp = []
                for j in range(n):
                    s = self._v_sign(self.instance.v_constraints[i][j])
                    vp.append(s if s else " ")
                lines.append("    ".join(vp))
        out = "\n".join(lines)

        self.out_text.config(state="normal")
        self.out_text.delete("1.0", "end")
        self.out_text.insert("1.0", out)
        self.out_text.config(state="disabled")
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

    def _reset(self):
        self.solution_grid = None
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
        if not fp:
            return
        with open(fp, "w", encoding="utf-8") as f:
            for row in self.solution_grid:
                f.write(" ".join(str(v) for v in row) + "\n")
        self.status.set(f"Saved: {fp}")


# ─────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    root.geometry("1000x660")
    FutoshikiGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()