"""Main application class orchestrating the Futoshiki Solver GUI.

This module wires together:
  - theme       (colors and font)
  - widgets     (reusable UI atoms)
  - solvers_loader (solver registry + animation)
  - metrics     (result normalization)
  - grid_view   (puzzle rendering)
  - chart       (performance chart)
  - exporter    (save / export / export_charts)

Everything related to drawing, exporting, or solver dispatch lives in
a focused module. The `App` class here manages UI state and user
interactions only.
"""
from __future__ import annotations
import sys
import time
import threading
import tracemalloc
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from queue import Queue, Empty

# Project path setup (lets us run `python -m Source.main`)
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Source.utils.parser import parse_futoshiki_file

from Source.gui.theme import PALETTE as P, FONT
from Source.gui.widgets import section_header, separator, action_button
from Source.gui.metrics import unpack as unpack_result
from Source.gui.solvers_loader import SOLVERS, register_solvers, animated_bt
from Source.gui.grid_view import draw_grid, format_solution
from Source.gui.chart import draw_chart
from Source.gui import exporter


class App:
    """Main application controller."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Futoshiki Solver")
        self.root.configure(bg=P["bg"])
        try: self.root.state("zoomed")
        except tk.TclError: pass

        # ── State ──
        self.inst = None            # parsed puzzle
        self.sol = None             # solved grid
        self.agrid = None           # animated grid snapshot
        self.ahl: dict[tuple[int, int], str] = {}  # highlighted cells
        self.anim_on = False
        self.anim_stop = [False]
        self.q: Queue | None = None
        self.steps = 0
        self.effort: dict[tuple[int, int], int] = {}
        self.show_heat = False
        self.cmp: dict = {}         # current puzzle comparison results
        self.chart_metric = "time"
        self.log_data: list[dict] = []
        self.last_logs: list[str] = []
        self.all_results: dict = {}  # cross-puzzle history for scalability

        self._build_ui()
        register_solvers()
        self.root.after(80, self._rebuild_algorithm_radios)

    # ═════════════════════════════════════════════════════════
    # UI construction
    # ═════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        self._build_top_bar()
        body = tk.Frame(self.root, bg=P["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=(6, 10))

        # Left sidebar
        left = tk.Frame(body, bg=P["panel"], width=220)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)
        self._build_sidebar(left)

        # Right panel (stats + chart + output)
        right = tk.Frame(body, bg=P["panel"], width=420)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)
        self._build_right_panel(right)

        # Center canvas (grid)
        self.canvas = tk.Canvas(body, bg=P["bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self._redraw_grid())

    def _build_top_bar(self) -> None:
        top = tk.Frame(self.root, bg=P["bg2"], height=50)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text=" FUTOSHIKI", font=(FONT, 20, "bold"),
                 fg=P["title"], bg=P["bg2"]).pack(side="left", padx=(20, 0))
        tk.Label(top, text="SOLVER", font=(FONT, 20),
                 fg=P["accent_h"], bg=P["bg2"]).pack(side="left", padx=(6, 0))

        rf = tk.Frame(top, bg=P["bg2"])
        rf.pack(side="right", padx=20)

        self.heat_var = tk.BooleanVar()
        tk.Checkbutton(rf, text="Heatmap", variable=self.heat_var,
                       command=self._toggle_heatmap,
                       font=(FONT, 9), fg=P["orange_h"], bg=P["bg2"],
                       selectcolor=P["panel"],
                       activebackground=P["bg2"],
                       activeforeground=P["orange_h"]
                       ).pack(side="right", padx=8)

        self.status = tk.StringVar(value="Load a puzzle to begin")
        tk.Label(rf, textvariable=self.status, font=(FONT, 9),
                 fg=P["sub"], bg=P["bg2"]).pack(side="right", padx=(0, 16))

    def _build_sidebar(self, parent: tk.Widget) -> None:
        # File section
        section_header(parent, "FILE")
        self.fvar = tk.StringVar(value="No file loaded")
        tk.Label(parent, textvariable=self.fvar, font=(FONT, 8),
                 fg=P["accent_h"], bg=P["panel"],
                 anchor="w", wraplength=190
                 ).pack(fill="x", padx=12, pady=(0, 3))
        action_button(parent, "Open File", self._on_open, P["accent"])
        separator(parent)

        # Algorithm selection
        section_header(parent, "ALGORITHM")
        self.algo = tk.StringVar()
        self._radio_frame = tk.Frame(parent, bg=P["panel"])
        self._radio_frame.pack(fill="x", padx=12)
        separator(parent)

        # Actions
        section_header(parent, "ACTIONS")
        action_button(parent, "▶   Solve",       self._on_solve,   P["green"])
        action_button(parent, "⏩  Animate",     self._on_animate, P["orange"])
        action_button(parent, "⚔   Compare All", self._on_compare, P["cyan"])
        action_button(parent, "⏹   Stop",        self._on_stop,    P["red"])
        separator(parent)

        # Speed slider
        sf = tk.Frame(parent, bg=P["panel"])
        sf.pack(fill="x", padx=12)
        tk.Label(sf, text="SPEED", font=(FONT, 7, "bold"),
                 fg=P["lbl"], bg=P["panel"]).pack(side="left")
        self.speed = tk.IntVar(value=80)
        tk.Scale(sf, from_=0, to=100, orient="horizontal",
                 variable=self.speed, showvalue=False,
                 bg=P["panel"], fg=P["num"],
                 troughcolor=P["cell"], highlightthickness=0
                 ).pack(side="left", fill="x", expand=True, padx=(6, 0))
        separator(parent)

        # Output actions
        action_button(parent, "⟲   Reset",          self._on_reset,         P["accent"])
        action_button(parent, "💾  Save Output",    self._on_save,          P["accent"])
        action_button(parent, "📊  Export Log",     self._on_export_log,    P["cyan"])
        action_button(parent, "📈  Export Charts",  self._on_export_charts, P["accent"])

    def _build_right_panel(self, parent: tk.Widget) -> None:
        # Statistics
        section_header(parent, "STATISTICS")
        self._stat_labels: dict[str, tk.Label] = {}
        sf = tk.Frame(parent, bg=P["panel"])
        sf.pack(fill="x", padx=14, pady=(0, 4))

        stat_rows = [
            ("status", "Status"),
            ("algo",   "Algorithm"),
            ("size",   "Grid"),
            ("time",   "Time"),
            ("mem",    "Memory"),
            ("steps",  "Inferences"),
        ]
        for idx, (key, label) in enumerate(stat_rows):
            tk.Label(sf, text=label, font=(FONT, 8),
                     fg=P["lbl"], bg=P["panel"], anchor="w"
                     ).grid(row=idx, column=0, sticky="w", padx=(0, 8))
            l = tk.Label(sf, text="-", font=(FONT, 10, "bold"),
                         fg=P["num"], bg=P["panel"], anchor="w")
            l.grid(row=idx, column=1, sticky="w")
            self._stat_labels[key] = l

        separator(parent)

        # Chart
        section_header(parent, "PERFORMANCE CHART")
        self._build_chart_tabs(parent)

        self.chart = tk.Canvas(parent, bg=P["chart_bg"],
                               highlightthickness=0, height=200)
        self.chart.pack(fill="x", padx=14, pady=(0, 4))

        separator(parent)

        # Output preview
        section_header(parent, "OUTPUT PREVIEW")
        self.out = tk.Text(parent, font=(FONT, 8),
                           fg=P["num"], bg=P["cell"],
                           relief="flat", wrap="none", state="disabled")
        self.out.pack(fill="both", expand=True, padx=14, pady=(0, 10))

    def _build_chart_tabs(self, parent: tk.Widget) -> None:
        tab_frame = tk.Frame(parent, bg=P["panel"])
        tab_frame.pack(fill="x", padx=14, pady=(0, 4))

        tabs = [
            ("time",        "Time (s)"),
            ("mem",         "Memory (KB)"),
            ("inferences",  "Inferences"),
            ("expansions",  "Expansions"),
        ]
        self.tab_btns: dict[str, tk.Label] = {}
        for metric, label in tabs:
            b = tk.Label(tab_frame, text=label, font=(FONT, 8, "bold"),
                         fg=P["title"], bg=P["tab_off"],
                         cursor="hand2", padx=10, pady=3)
            b.bind("<Button-1>", lambda _e, m=metric: self._set_chart_metric(m))
            b.pack(side="left", padx=(0, 3))
            self.tab_btns[metric] = b
        self._update_tab_styles()

    def _rebuild_algorithm_radios(self) -> None:
        for w in self._radio_frame.winfo_children():
            w.destroy()
        names = list(SOLVERS.keys()) or ["(none)"]
        self.algo.set(names[0])
        for name in names:
            tk.Radiobutton(self._radio_frame, text=name,
                           variable=self.algo, value=name,
                           font=(FONT, 9), fg=P["num"],
                           bg=P["panel"], selectcolor=P["cell"],
                           activebackground=P["panel"],
                           activeforeground=P["num"],
                           anchor="w").pack(fill="x")

    # ═════════════════════════════════════════════════════════
    # Small UI state helpers
    # ═════════════════════════════════════════════════════════

    def _set_stat(self, key: str, value, color: str | None = None) -> None:
        label = self._stat_labels.get(key)
        if label:
            label.config(text=str(value))
            if color:
                label.config(fg=color)

    def _clear_stats(self) -> None:
        for label in self._stat_labels.values():
            label.config(text="-", fg=P["num"])
        self.out.config(state="normal")
        self.out.delete("1.0", "end")
        self.out.config(state="disabled")

    def _set_chart_metric(self, metric: str) -> None:
        self.chart_metric = metric
        self._update_tab_styles()
        self._redraw_chart()

    def _update_tab_styles(self) -> None:
        for metric, btn in self.tab_btns.items():
            if metric == self.chart_metric:
                btn.config(bg=P["tab_on"], fg=P["title"])
            else:
                btn.config(bg=P["tab_off"], fg=P["lbl"])

    def _redraw_grid(self) -> None:
        draw_grid(self.canvas, self.inst,
                  sol=self.sol, agrid=self.agrid, ahl=self.ahl,
                  effort=self.effort, show_heat=self.show_heat)

    def _redraw_chart(self) -> None:
        draw_chart(self.chart, self.cmp, self.chart_metric)

    def _write_output(self, grid: list[list[int]]) -> None:
        text = format_solution(self.inst, grid)
        self.out.config(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)
        self.out.config(state="disabled")

    # ═════════════════════════════════════════════════════════
    # Event handlers
    # ═════════════════════════════════════════════════════════

    def _on_open(self) -> None:
        if self.anim_on:
            messagebox.showwarning("", "Stop animation first.")
            return

        default_dir = _ROOT / "Inputs"
        fp = filedialog.askopenfilename(
            initialdir=str(default_dir) if default_dir.exists() else str(_ROOT),
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
        )
        if not fp:
            return

        try:
            self.inst = parse_futoshiki_file(Path(fp))
            self.sol = None
            self.agrid = None
            self.ahl = {}
            self.effort = {}
            self.show_heat = False
            self.heat_var.set(False)
            self.cmp = {}
            self.chart.delete("all")

            self.fvar.set(Path(fp).name)
            self._clear_stats()
            self._set_stat("size", f"{self.inst.n} x {self.inst.n}")
            self._set_stat("status", "Ready", P["snum"])
            self._redraw_grid()
            self.status.set(f"Loaded {Path(fp).name}")
        except Exception as e:
            self._set_stat("status", "Invalid input", P["red_h"])
            self.status.set(f"Parse error: {str(e)[:80]}")
            messagebox.showerror(
                "Invalid Input File",
                f"Cannot parse file:\n\n{Path(fp).name}\n\nReason:\n{e}",
            )

    def _on_solve(self) -> None:
        if not self.inst:
            messagebox.showwarning("", "Open a file first.")
            return
        if self.anim_on:
            messagebox.showwarning("", "Stop animation first.")
            return

        name = self.algo.get()
        fn = SOLVERS.get(name)
        if not fn:
            messagebox.showerror("", f"'{name}' not found.")
            return

        self.agrid = None
        self.ahl = {}
        self._set_stat("status", "Solving...", P["orange_h"])
        self._set_stat("algo", name)
        self.status.set(f"Solving with {name}...")
        self.root.update()

        threading.Thread(target=self._run_solver,
                         args=(fn, name), daemon=True).start()

    def _run_solver(self, fn, name: str) -> None:
        try:
            tracemalloc.start()
            t0 = time.perf_counter()
            result = fn(self.inst)
            grid, metrics, logs = unpack_result(result)
            elapsed = time.perf_counter() - t0
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            stats = {
                "time": round(elapsed, 4),
                "mem": round(peak / 1024, 2),
                "steps": metrics,
            }
            if grid is None:
                self.root.after(0, self._on_no_solution)
            else:
                self.root.after(0, lambda: self._on_solved(grid, stats, name, logs))
        except NotImplementedError as e:
            self.root.after(0, lambda: self._on_not_implemented(str(e)))
        except Exception as e:
            self.root.after(0, lambda: self._on_error(str(e)))

    def _on_solved(self, grid: list[list[int]], stats: dict,
                   name: str, logs: list[str]) -> None:
        self.last_logs = logs or []
        self.sol = grid

        metrics = stats["steps"]
        inferences = metrics.get("inferences", 0)
        expansions = metrics.get("expansions", 0)

        self._set_stat("status", "Solved", P["snum"])
        self._set_stat("time", f"{stats['time']}s")
        self._set_stat("mem",  f"{stats['mem']} KB")
        self._set_stat("steps", f"Inferences: {inferences}  |  Expansions: {expansions}")
        self.status.set(f"Solved by {name} in {stats['time']}s")

        self._redraw_grid()
        self._write_output(grid)

        # Update comparison + history
        self.cmp[name] = {
            "time": stats["time"], "mem": stats["mem"],
            "inferences": inferences, "expansions": expansions,
            "ok": True,
        }
        self._log_result(name, stats["time"], stats["mem"], inferences, expansions)
        self._redraw_chart()

    def _log_result(self, name: str, t: float, mem: float,
                    inf: int, exp: int) -> None:
        """Append to log_data + all_results for history tracking."""
        entry = {
            "input": self.fvar.get(),
            "grid_size": f"{self.inst.n}x{self.inst.n}",
            "algo": name,
            "time": t, "mem": mem,
            "inferences": inf, "expansions": exp,
        }
        self.log_data.append(entry)

        inp = self.fvar.get()
        self.all_results.setdefault(inp, {})
        self.all_results[inp][name] = {
            "time": t, "mem": mem,
            "inferences": inf, "expansions": exp,
            "n": self.inst.n,
        }

    def _on_no_solution(self) -> None:
        self._set_stat("status", "No solution", P["red_h"])
        self.status.set("No solution.")

    def _on_not_implemented(self, msg: str) -> None:
        self._set_stat("status", "N/A", P["orange_h"])
        self.status.set(msg)
        messagebox.showinfo("", msg)

    def _on_error(self, msg: str) -> None:
        self._set_stat("status", "Error", P["red_h"])
        self.status.set(msg)
        messagebox.showerror("", msg)

    # ── Animation ──

    def _on_animate(self) -> None:
        if not self.inst:
            messagebox.showwarning("", "Open a file first.")
            return
        if self.anim_on:
            return

        self.anim_on = True
        self.anim_stop = [False]
        self.sol = None
        self.agrid = [r[:] for r in self.inst.grid]
        self.ahl = {}
        self.steps = 0
        self.effort = {}
        self.show_heat = False
        self.heat_var.set(False)
        self.q = Queue()
        self._clear_stats()
        self._set_stat("status", "Animating...", P["orange_h"])
        self._set_stat("algo", "Backtracking")
        self._set_stat("size", f"{self.inst.n} x {self.inst.n}")
        self.status.set("Animation running...")

        threading.Thread(target=animated_bt,
                         args=(self.inst, self.q, self.anim_stop),
                         daemon=True).start()
        self._poll_animation()

    def _poll_animation(self) -> None:
        if not self.anim_on:
            return

        spd = self.speed.get()
        delay = max(1, int(350 * (1 - spd / 100) ** 2))
        batch = max(1, spd // 12)

        for _ in range(batch):
            try:
                step = self.q.get_nowait()
            except Empty:
                break

            kind = step[0]
            if kind == "try":
                _, r, c, vl, ef = step
                self.steps += 1
                self.effort = ef
                self.agrid[r][c] = vl
                self.ahl = {(r, c): P["trying"]}
                self._set_stat("steps", str(self.steps))
            elif kind == "set":
                _, r, c, vl = step
                self.agrid[r][c] = vl
                self.ahl = {(r, c): P["solved"]}
            elif kind == "fail":
                _, r, c, vl = step
                self.agrid[r][c] = 0
                self.ahl = {(r, c): P["fail"]}
            elif kind == "undo":
                _, r, c = step
                self.agrid[r][c] = 0
                self.ahl = {(r, c): P["fail"]}
            elif kind == "done":
                _, grid, ef = step
                self.sol = grid
                self.effort = ef
                self.agrid = None
                self.ahl = {}
                self.anim_on = False
                self._set_stat("status", "Solved", P["snum"])
                self._redraw_grid()
                self._write_output(grid)
                self.status.set(f"Done - {self.steps} steps")
                return
            elif kind == "nosoln":
                self.anim_on = False
                self.agrid = None
                self.ahl = {}
                self._set_stat("status", "No solution", P["red_h"])
                self._redraw_grid()
                return

        self._redraw_grid()
        self.root.after(delay, self._poll_animation)

    def _on_stop(self) -> None:
        if self.anim_on:
            self.anim_stop[0] = True
            self.anim_on = False
            self.agrid = None
            self.ahl = {}
            self._set_stat("status", "Stopped", P["orange_h"])
            self._redraw_grid()
            self.status.set("Stopped.")

    # ── Compare all ──

    def _on_compare(self) -> None:
        if not self.inst:
            messagebox.showwarning("", "Open a file first.")
            return
        if self.anim_on:
            messagebox.showwarning("", "Stop animation first.")
            return

        self._set_stat("status", "Comparing...", P["orange_h"])
        self.status.set("Running all algorithms...")
        self.root.update()
        threading.Thread(target=self._run_comparison, daemon=True).start()

    def _run_comparison(self) -> None:
        results: dict = {}
        timeout = 10

        for name, fn in SOLVERS.items():
            self.root.after(0, lambda n=name: self.status.set(f"Running {n}..."))
            box: list = [None, 0, 0, {"inferences": 0, "expansions": 0}]

            def worker(f=fn):
                try:
                    tracemalloc.start()
                    t0 = time.perf_counter()
                    res = f(self.inst)
                    grid, metrics, _ = unpack_result(res)
                    elapsed = time.perf_counter() - t0
                    _, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    box[0] = grid
                    box[1] = round(elapsed, 4)
                    box[2] = round(peak / 1024, 2)
                    box[3] = metrics
                except NotImplementedError:
                    box[0] = "NI"
                except Exception:
                    box[0] = "ERR"

            th = threading.Thread(target=worker, daemon=True)
            th.start()
            th.join(timeout=timeout)

            if th.is_alive():
                results[name] = {"time": timeout, "mem": 0,
                                 "inferences": 0, "expansions": 0,
                                 "ok": False, "note": "timeout"}
            elif box[0] in ("NI", "ERR"):
                results[name] = {"time": 0, "mem": 0,
                                 "inferences": 0, "expansions": 0,
                                 "ok": None}
            else:
                metrics = box[3]
                if isinstance(metrics, dict):
                    inf = metrics.get("inferences", 0)
                    exp = metrics.get("expansions", 0)
                else:
                    inf = int(metrics) if metrics else 0
                    exp = inf
                results[name] = {
                    "time": box[1], "mem": box[2],
                    "inferences": inf, "expansions": exp,
                    "ok": True,
                }

        self.root.after(0, lambda: self._on_comparison_done(results))

    def _on_comparison_done(self, results: dict) -> None:
        self.cmp = results
        self._redraw_chart()

        for name, info in results.items():
            if info.get("ok"):
                self._log_result(name, info["time"], info["mem"],
                                 info.get("inferences", 0),
                                 info.get("expansions", 0))

        solved = [k for k, v in results.items() if v.get("ok")]
        if solved:
            fastest = min(solved, key=lambda k: results[k]["time"])
            self._set_stat("status", f"Winner: {fastest}", P["snum"])
            self._set_stat("algo", fastest)
            self._set_stat("time", f"{results[fastest]['time']}s")
            self._set_stat("mem",  f"{results[fastest]['mem']} KB")
            self.status.set(f"Fastest: {fastest} ({results[fastest]['time']}s)")
        else:
            self._set_stat("status", "No solver OK", P["red_h"])

    # ── Heatmap ──

    def _toggle_heatmap(self) -> None:
        self.show_heat = self.heat_var.get()
        self._redraw_grid()

    # ── Save / Export ──

    def _on_save(self) -> None:
        if not self.sol:
            messagebox.showwarning("", "No solution.")
            return
        name = exporter.save_solution(self.inst, self.sol, _ROOT)
        if name:
            self.status.set(f"Saved: {name}")

    def _on_export_log(self) -> None:
        name = exporter.export_log(_ROOT, self.log_data, self.last_logs,
                                   self.fvar.get(), self.inst)
        if name:
            suffix = "CSV" if name.endswith(".csv") else "Log"
            self.status.set(f"{suffix} exported: {name}")

    def _on_export_charts(self) -> None:
        saved = exporter.export_charts(_ROOT, self.cmp, self.all_results,
                                       self.fvar.get())
        if saved:
            self.status.set(f"Exported {len(saved)} charts")

    # ── Reset ──

    def _on_reset(self) -> None:
        if self.anim_on:
            self._on_stop()
        self.sol = None
        self.agrid = None
        self.ahl = {}
        self.effort = {}
        self.show_heat = False
        self.heat_var.set(False)
        self.cmp = {}
        self.chart.delete("all")
        self.log_data = []
        self.last_logs = []
        self._clear_stats()
        if self.inst:
            self._set_stat("size", f"{self.inst.n} x {self.inst.n}")
            self._set_stat("status", "Ready", P["snum"])
        self._redraw_grid()
        self.status.set("Reset.")


# ═════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════

def main() -> None:
    root = tk.Tk()
    root.geometry("1300x800")
    try: root.state("zoomed")
    except tk.TclError: pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
