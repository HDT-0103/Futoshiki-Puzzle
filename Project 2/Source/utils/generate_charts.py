#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for row in rows:
        if row.get("size"):
            size_value = row["size"]
        else:
            input_name = row.get("input_file") or row.get("input") or ""
            digits = "".join(ch for ch in input_name if ch.isdigit())
            size_value = digits.lstrip("0") or digits or "0"

        peak_memory = row.get("peak_memory_mb")
        if peak_memory is None:
            peak_memory = row.get("peak_kb", "0")

        normalized.append(
            {
                "algorithm": row.get("algorithm", ""),
                "size": size_value,
                "runtime_ms": row.get("runtime_ms", "0"),
                "peak_memory_mb": peak_memory,
                "nodes_expanded": row.get("nodes_expanded", "0"),
                "solved": row.get("solved", row.get("success", "0")),
            }
        )
    return normalized


def build_series(rows: list[dict[str, str]], metric: str) -> dict[str, list[tuple[int, float]]]:
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)
    for row in rows:
        size_text = row.get("size", "0")
        size = int(size_text) if str(size_text).isdigit() else 0
        grouped[(row["algorithm"], size)].append(float(row[metric]))

    out: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for (algo, size), values in grouped.items():
        out[algo].append((size, avg(values)))
    for algo in out:
        out[algo].sort(key=lambda item: item[0])
    return out


def plot_metric(series: dict[str, list[tuple[int, float]]], title: str, ylabel: str, output_path: Path) -> None:
    if not series:
        raise ValueError(f"No data available for {title}")

    plt.figure(figsize=(10, 6))
    colors = {
        "fc": "#1f77b4",
        "bc": "#ff7f0e",
        "astar": "#2ca02c",
        "bt": "#d62728",
        "bf": "#9467bd",
    }

    for algo in sorted(series):
        xs = [size for size, _ in series[algo]]
        ys = [value for _, value in series[algo]]
        plt.plot(xs, ys, marker="o", linewidth=2, label=algo, color=colors.get(algo))

    plt.title(title, fontsize=14, fontweight="bold")
    plt.xlabel("Grid size N", fontsize=12, fontweight="bold")
    plt.ylabel(ylabel, fontsize=12, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=180)
    plt.close()
    print(f"Wrote: {output_path}")


def generate_chart_pngs(benchmark_csv: Path, chart_dir: Path) -> None:
    rows = read_rows(benchmark_csv)
    if not rows:
        raise ValueError("Benchmark CSV is empty")

    rows = normalize_rows(rows)

    runtime_series = build_series(rows, "runtime_ms")
    memory_series = build_series(rows, "peak_memory_mb")
    nodes_series = build_series(rows, "nodes_expanded")

    plot_metric(runtime_series, "Algorithm Runtime Comparison", "Runtime (ms)", chart_dir / "runtime_comparison.png")
    plot_metric(memory_series, "Algorithm Memory Usage Comparison", "Peak Memory (MB)", chart_dir / "memory_comparison.png")
    plot_metric(nodes_series, "Algorithm Search Nodes Comparison", "Nodes Expanded", chart_dir / "nodes_comparison.png")

    algorithms = sorted(runtime_series)
    avg_runtime = [avg([value for _, value in runtime_series[algo]]) for algo in algorithms]
    avg_memory = [avg([value for _, value in memory_series[algo]]) for algo in algorithms]
    avg_nodes = [avg([value for _, value in nodes_series[algo]]) for algo in algorithms]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    x = list(range(len(algorithms)))
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    axes[0, 0].bar(x, avg_runtime, color=palette[: len(algorithms)])
    axes[0, 0].set_title("Average Runtime", fontweight="bold")
    axes[0, 0].set_ylabel("ms")
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(algorithms)
    axes[0, 0].grid(axis="y", alpha=0.3)

    axes[0, 1].bar(x, avg_memory, color=palette[: len(algorithms)])
    axes[0, 1].set_title("Average Peak Memory", fontweight="bold")
    axes[0, 1].set_ylabel("MB")
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(algorithms)
    axes[0, 1].grid(axis="y", alpha=0.3)

    axes[1, 0].bar(x, avg_nodes, color=palette[: len(algorithms)])
    axes[1, 0].set_title("Average Nodes Expanded", fontweight="bold")
    axes[1, 0].set_ylabel("nodes")
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(algorithms)
    axes[1, 0].grid(axis="y", alpha=0.3)

    axes[1, 1].axis("off")
    summary_rows = [[algo, f"{avg_runtime[i]:.2f}", f"{avg_memory[i]:.4f}", f"{avg_nodes[i]:.0f}"] for i, algo in enumerate(algorithms)]
    table = axes[1, 1].table(
        cellText=summary_rows,
        colLabels=["Algo", "Runtime", "Memory", "Nodes"],
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.6)

    plt.tight_layout()
    summary_path = chart_dir / "summary_statistics.png"
    chart_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(summary_path, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"Wrote: {summary_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate benchmark charts as PNG images.")
    parser.add_argument(
        "benchmark_csv",
        nargs="?",
        type=Path,
        default=PROJECT_ROOT / "assets" / "benchmark" / "benchmark_result.csv",
    )
    parser.add_argument(
        "chart_output_dir",
        nargs="?",
        type=Path,
        default=PROJECT_ROOT / "assets" / "benchmark",
    )
    args = parser.parse_args()

    benchmark_csv = args.benchmark_csv
    if not benchmark_csv.exists():
        fallback = PROJECT_ROOT / "assets" / "benchmak" / "benchmark_result.csv"
        if fallback.exists():
            benchmark_csv = fallback

    generate_chart_pngs(benchmark_csv, args.chart_output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
