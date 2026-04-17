from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

FIG_BG = "#e6e6e6"
AX_BG = "#e6e6e6"
BAR_COLOR = "#2b579a"
BAR_EDGE = "#1f3f72"
GRID_COLOR = "#c7c7c7"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for row in rows:
        input_name = row.get("input_file") or row.get("input") or ""
        digits = "".join(ch for ch in input_name if ch.isdigit())
        size_value = row.get("size") or (digits.lstrip("0") or digits or "0")

        runtime_s = row.get("running_time_s", row.get("runtime_s", "0"))
        memory_usage_mb = row.get("memory_usage_mb", row.get("peak_mb", "0"))
        inferences = row.get("inferences", row.get("inferences_expansions", "0"))
        expansions = row.get("expansions", row.get("nodes_expanded", row.get("inferences_expansions", "0")))

        normalized.append(
            {
                "input_file": row.get("input_file", row.get("input", "")),
                "algorithm": row.get("algorithm", ""),
                "size": size_value,
                "runtime_s": runtime_s,
                "memory_usage_mb": memory_usage_mb,
                "inferences": inferences,
                "expansions": expansions,
            }
        )
    return normalized


def algo_display_name(algo: str) -> str:
    if algo in {"a_star", "astar"}:
        return "A*"
    return algo.upper()


def algo_radar_label(algo: str) -> str:
    if algo in {"a_star", "astar"}:
        return "A_STAR"
    return algo.upper()


def algo_order(algorithms: set[str]) -> list[str]:
    preferred = ["bfs", "dfs", "ucs", "a_star", "astar", "fc", "bc", "bt", "bf"]
    ordered = [a for a in preferred if a in algorithms]
    for algo in sorted(algorithms):
        if algo not in ordered:
            ordered.append(algo)
    return ordered


def aggregate_algorithm_metrics(rows: list[dict[str, str]]) -> tuple[list[str], dict[str, dict[str, float]], int]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    inputs: set[str] = set()
    for row in rows:
        algo = row.get("algorithm", "")
        if not algo:
            continue
        grouped[algo].append(row)
        input_name = row.get("input_file", "")
        if input_name:
            inputs.add(input_name)

    algorithms = algo_order(set(grouped.keys()))
    summary: dict[str, dict[str, float]] = {}
    for algo in algorithms:
        group = grouped[algo]
        summary[algo] = {
            "avg_runtime_s": avg([float(r.get("runtime_s", "0") or "0") for r in group]),
            "avg_memory_mb": avg([float(r.get("memory_usage_mb", "0") or "0") for r in group]),
            "avg_inferences": avg([float(r.get("inferences", "0") or "0") for r in group]),
            "avg_expansions": avg([float(r.get("expansions", "0") or "0") for r in group]),
        }

    return algorithms, summary, len(inputs)


def rank_scores(values: list[float], *, lower_is_better: bool) -> list[float]:
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [1.0]

    order = sorted(range(n), key=lambda i: values[i], reverse=not lower_is_better)
    scores = [0.0] * n
    for rank, idx in enumerate(order):
        scores[idx] = 1.0 - (rank / (n - 1))
    return scores


def plot_average_bar_chart(
    algorithms: list[str],
    values: list[float],
    title: str,
    y_label: str,
    value_format: str,
    output_path: Path,
    *,
    use_symlog: bool = False,
    symlog_linthresh: float = 1.0,
) -> None:
    if not algorithms:
        return

    x_labels = [algo_display_name(a) for a in algorithms]
    fig, ax = plt.subplots(figsize=(10.8, 6.4), dpi=180)
    fig.patch.set_facecolor(FIG_BG)
    ax.set_facecolor(AX_BG)
    bars = ax.bar(x_labels, values, color=BAR_COLOR, edgecolor=BAR_EDGE, linewidth=0.8)

    ax.set_title(title, fontsize=17, fontweight="bold", pad=12)
    ax.set_xlabel("Algorithm", fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.grid(axis="y", linestyle="--", color=GRID_COLOR, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444444")
    ax.spines["bottom"].set_color("#444444")

    if use_symlog:
        ax.set_yscale("symlog", linthresh=symlog_linthresh)

    max_value = max(values) if values else 0
    upper = max_value * 1.12 if max_value > 0 else 1.0
    ax.set_ylim(0, upper)

    text_offset = upper * 0.01
    for bar, value in zip(bars, values):
        if use_symlog:
            label_y = value + max(value * 0.05, symlog_linthresh * 0.15)
        else:
            label_y = bar.get_height() + text_offset
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            label_y,
            value_format.format(value),
            ha="center",
            va="bottom",
            fontsize=10,
            color="#2a2a2a",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"Wrote: {output_path}")
