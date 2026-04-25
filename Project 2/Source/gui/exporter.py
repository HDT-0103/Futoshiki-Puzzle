"""Export handlers for solution files, logs, and charts.

Functions here are invoked from the main App but kept separate to
keep `app.py` focused on UI orchestration.
"""
from __future__ import annotations
import csv
from pathlib import Path
from tkinter import filedialog, messagebox

from Source.gui.grid_view import format_solution


# ═════════════════════════════════════════════════════════════
# Solution file export
# ═════════════════════════════════════════════════════════════

def save_solution(inst, solution: list[list[int]], root_dir: Path) -> str | None:
    """Write the solved grid to a user-chosen file. Returns filename or None."""
    default_dir = root_dir / "Outputs"
    fp = filedialog.asksaveasfilename(
        initialdir=str(default_dir),
        defaultextension=".txt",
        filetypes=[("Text", "*.txt")],
    )
    if not fp:
        return None

    with open(fp, "w", encoding="utf-8") as f:
        f.write(format_solution(inst, solution))

    return Path(fp).name


# ═════════════════════════════════════════════════════════════
# Log export (CSV statistics or TXT step detail)
# ═════════════════════════════════════════════════════════════

def export_log(root_dir: Path, log_data: list[dict], last_logs: list[str],
               input_name: str, inst) -> str | None:
    """Save either a CSV with statistics or a TXT with per-step details."""
    if not log_data and not last_logs:
        messagebox.showwarning("", "No data. Run Solve or Compare first.")
        return None

    default_dir = root_dir / "Outputs"
    fp = filedialog.asksaveasfilename(
        initialdir=str(default_dir),
        defaultextension=".csv",
        filetypes=[("CSV (statistics)", "*.csv"),
                   ("TXT (step detail)", "*.txt")],
    )
    if not fp:
        return None

    if fp.endswith(".csv"):
        _write_csv(fp, log_data)
    else:
        _write_txt(fp, input_name, inst, last_logs)

    return Path(fp).name


def _write_csv(fp: str, log_data: list[dict]) -> None:
    with open(fp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "input", "grid_size", "algo", "time", "mem",
            "inferences", "expansions",
        ])
        writer.writeheader()
        for row in log_data:
            writer.writerow(row)


def _write_txt(fp: str, input_name: str, inst,
               last_logs: list[str]) -> None:
    with open(fp, "w", encoding="utf-8") as f:
        f.write("=== Futoshiki Solver Log ===\n")
        f.write(f"Input: {input_name}\n")
        if inst:
            f.write(f"Grid: {inst.n}x{inst.n}\n")
        f.write(f"Total steps: {len(last_logs)}\n")
        f.write("=" * 40 + "\n\n")
        for line in last_logs:
            f.write(line + "\n")


# ═════════════════════════════════════════════════════════════
# Chart export (PNG via matplotlib)
# ═════════════════════════════════════════════════════════════

SOLVER_COLORS = {
    "Backtracking":      "#50ff90",
    "Brute Force":       "#ff5060",
    "Forward Chaining":  "#ffd050",
    "Backward Chaining": "#c0a0ff",
    "A* Search":         "#20d0e0",
    "Built-in BT":       "#50ff90",
}

DARK_BG = "#0c1028"
GRID_COLOR = "#283060"
TEXT_COLOR = "#d4d0f0"
LABEL_COLOR = "#9090b8"


def export_charts(root_dir: Path, cmp: dict, all_results: dict,
                  input_name: str) -> list[str] | None:
    """Export comparison, scalability, and per-algorithm detail charts.

    Returns the list of saved filenames, or None if cancelled/failed.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        messagebox.showerror("", "matplotlib is required:\npip install matplotlib")
        return None

    if not cmp and not all_results:
        messagebox.showwarning("", "No data. Run Solve or Compare first.")
        return None

    default_dir = root_dir / "Outputs"
    folder_str = filedialog.askdirectory(
        title="Choose folder to save charts",
        initialdir=str(default_dir),
    )
    if not folder_str:
        return None

    folder = Path(folder_str)
    _apply_plot_style(plt)

    saved: list[str] = []
    saved += _export_comparison_charts(plt, folder, cmp, input_name)
    saved += _export_scalability_charts(plt, folder, all_results)
    saved += _export_detail_charts(plt, folder, cmp, input_name)

    if not saved:
        messagebox.showwarning("", "No charts generated. Need more data.")
        return None

    messagebox.showinfo(
        "Export Complete",
        f"Saved {len(saved)} charts:\n\n" + "\n".join(saved),
    )
    return saved


# ── Matplotlib styling ──

def _apply_plot_style(plt) -> None:
    plt.rcParams.update({
        "figure.facecolor": DARK_BG,
        "axes.facecolor":   DARK_BG,
        "axes.edgecolor":   GRID_COLOR,
        "axes.labelcolor":  TEXT_COLOR,
        "xtick.color":      LABEL_COLOR,
        "ytick.color":      LABEL_COLOR,
        "text.color":       TEXT_COLOR,
        "grid.color":       GRID_COLOR,
        "grid.alpha":       0.3,
        "font.family":      "monospace",
        "font.size":        10,
    })


# ── Metric extraction (handles legacy formats) ──

def _get_metric(info: dict, metric: str) -> int | float:
    if metric in ("inferences", "expansions"):
        v = info.get(metric)
        if v is not None:
            return int(v)
        steps = info.get("steps")
        if isinstance(steps, dict):
            return int(steps.get(metric, 0))
        if isinstance(steps, (int, float)):
            return int(steps)
        return 0
    return info.get(metric, 0)


# ── Chart 1: Side-by-side comparison of all solvers on current puzzle ──

def _export_comparison_charts(plt, folder: Path, cmp: dict,
                              input_name: str) -> list[str]:
    if not cmp:
        return []
    ok = {k: v for k, v in cmp.items() if v.get("ok")}
    if not ok:
        return []

    saved = []
    metrics_config = [
        ("time",        "s",  "Time"),
        ("mem",         "KB", "Memory"),
        ("inferences",  "",   "Inferences"),
        ("expansions",  "",   "Expansions"),
    ]

    for metric, unit, title in metrics_config:
        names = list(ok.keys())
        vals = [_get_metric(ok[n], metric) for n in names]
        if all(v == 0 for v in vals):
            continue

        fig, ax = plt.subplots(figsize=(8, 5))
        cols = [SOLVER_COLORS.get(n, "#888") for n in names]
        bars = ax.bar(names, vals, color=cols, edgecolor="none", width=0.6)

        for bar, val in zip(bars, vals):
            fmt = _format_value(metric, val, unit)
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    fmt, ha="center", va="bottom", fontsize=9, color=TEXT_COLOR)

        ax.set_title(f"{title} Comparison — {input_name}", fontsize=13, pad=12)
        ax.set_ylabel(f"{title} ({unit})" if unit else title)
        ax.grid(axis="y", linestyle="--")
        plt.xticks(rotation=15, ha="right")
        plt.tight_layout()

        path = folder / f"compare_{metric}.png"
        fig.savefig(path, dpi=150, facecolor=DARK_BG)
        plt.close(fig)
        saved.append(path.name)

    return saved


# ── Chart 2: Scalability (multiple puzzles at different N) ──

def _export_scalability_charts(plt, folder: Path,
                               all_results: dict) -> list[str]:
    if not all_results or len(all_results) < 2:
        return []

    # Re-organize: {algo: [(n, time, inferences, expansions), ...]}
    algo_data: dict[str, list[tuple]] = {}
    for inp, algos in all_results.items():
        for algo, info in algos.items():
            algo_data.setdefault(algo, []).append((
                info["n"],
                info["time"],
                _get_metric(info, "inferences"),
                _get_metric(info, "expansions"),
            ))

    for algo in algo_data:
        algo_data[algo].sort(key=lambda x: x[0])

    saved = []
    configs = [
        (1, "Time (s)",    "Scalability: Grid Size vs Time",        "scalability_time"),
        (2, "Inferences",  "Scalability: Grid Size vs Inferences",  "scalability_inferences"),
        (3, "Expansions",  "Scalability: Grid Size vs Expansions",  "scalability_expansions"),
    ]

    for idx, ylabel, title, fname in configs:
        fig, ax = plt.subplots(figsize=(9, 5.5))
        has_data = False

        for algo, data in algo_data.items():
            ns = [d[0] for d in data]
            vs = [d[idx] for d in data]
            if any(v > 0 for v in vs):
                has_data = True
                color = SOLVER_COLORS.get(algo, "#888")
                ax.plot(ns, vs, "o-", color=color, label=algo,
                        linewidth=2, markersize=7)

        if not has_data:
            plt.close(fig)
            continue

        ax.set_xlabel("Grid Size (N)")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=13, pad=12)
        ax.legend(facecolor=DARK_BG, edgecolor=GRID_COLOR, fontsize=9)
        ax.grid(True, linestyle="--")

        # Log scale if spread is very large
        all_vs = [d[idx] for data in algo_data.values() for d in data if d[idx] > 0]
        if all_vs and max(all_vs) / max(min(all_vs), 0.0001) > 100:
            ax.set_yscale("log")
            ax.set_ylabel(f"{ylabel} (log scale)")

        plt.tight_layout()
        path = folder / f"{fname}.png"
        fig.savefig(path, dpi=150, facecolor=DARK_BG)
        plt.close(fig)
        saved.append(path.name)

    return saved


# ── Chart 3: Per-algorithm detail on current puzzle ──

def _export_detail_charts(plt, folder: Path, cmp: dict,
                          input_name: str) -> list[str]:
    if not cmp:
        return []

    saved = []
    ok = {k: v for k, v in cmp.items() if v.get("ok")}

    for algo, info in ok.items():
        fig, axes = plt.subplots(1, 4, figsize=(14, 4))
        panels = [
            ("time",        "Time (s)",    f"{info['time']:.4f}s"),
            ("mem",         "Memory (KB)", f"{info['mem']:.1f}KB"),
            ("inferences",  "Inferences",  f"{_get_metric(info, 'inferences')}"),
            ("expansions",  "Expansions",  f"{_get_metric(info, 'expansions')}"),
        ]
        color = SOLVER_COLORS.get(algo, "#888")

        for ax, (key, label, val_str) in zip(axes, panels):
            val = _get_metric(info, key)
            ax.bar([label], [val], color=color, width=0.5)
            ax.text(0, val, val_str, ha="center", va="bottom",
                    fontsize=11, color=TEXT_COLOR)
            ax.set_title(label, fontsize=10)
            ax.grid(axis="y", linestyle="--")

        fig.suptitle(f"{algo} — {input_name}", fontsize=13)
        plt.tight_layout()

        safe_name = algo.replace(" ", "_").replace("*", "star")
        path = folder / f"detail_{safe_name}.png"
        fig.savefig(path, dpi=150, facecolor=DARK_BG)
        plt.close(fig)
        saved.append(path.name)

    return saved


def _format_value(metric: str, val: float, unit: str) -> str:
    if metric == "time":
        return f"{val:.4f}{unit}"
    if metric == "mem":
        return f"{val:.1f}{unit}"
    return f"{int(val)}"
