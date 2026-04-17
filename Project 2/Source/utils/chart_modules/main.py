from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Source.utils.chart_modules import (
    render_expansions_chart,
    render_inferences_chart,
    render_memory_chart,
    render_overview_chart,
    render_runtime_chart,
    render_summary_table_4features,
)
from Source.utils.chart_modules.common import aggregate_algorithm_metrics, normalize_rows, read_rows


def _cleanup_old_outputs(chart_dir: Path) -> None:
    old_files = [
        "runtime_comparison.png",
        "memory_comparison.png",
        "nodes_comparison.png",
        "runtime_by_case.png",
        "memory_by_case.png",
        "inferences_by_case.png",
        "expansions_by_case.png",
        "summary_statistics.png",
        "table_algorithm_summary.png",
        "table_case_by_case.png",
        "summary_table_3features.png",
        "summary_table_4features.png",
        "overview_performance_radar.png",
    ]
    for name in old_files:
        path = chart_dir / name
        if path.exists():
            path.unlink()


def generate_chart_pngs(benchmark_csv: Path, chart_dir: Path) -> None:
    rows = read_rows(benchmark_csv)
    if not rows:
        raise ValueError("Benchmark CSV is empty")

    rows = normalize_rows(rows)
    chart_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_old_outputs(chart_dir)
    algorithms, summary, case_count = aggregate_algorithm_metrics(rows)

    render_runtime_chart(algorithms, summary, chart_dir, case_count)
    render_memory_chart(algorithms, summary, chart_dir, case_count)
    render_inferences_chart(algorithms, summary, chart_dir, case_count)
    render_expansions_chart(algorithms, summary, chart_dir, case_count)
    render_summary_table_4features(algorithms, summary, chart_dir, case_count)
    render_overview_chart(algorithms, summary, chart_dir, case_count)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate benchmark charts as PNG images.")
    parser.add_argument(
        "benchmark_csv",
        nargs="?",
        type=Path,
        default=PROJECT_ROOT / "Source" / "assets" / "benchmark" / "benchmark_result.csv",
    )
    parser.add_argument(
        "chart_output_dir",
        nargs="?",
        type=Path,
        default=PROJECT_ROOT / "Source" / "assets" / "benchmark",
    )
    args = parser.parse_args()

    benchmark_csv = args.benchmark_csv
    if not benchmark_csv.exists():
        fallback = PROJECT_ROOT / "Source" / "assets" / "benchmak" / "benchmark_result.csv"
        if fallback.exists():
            benchmark_csv = fallback

    generate_chart_pngs(benchmark_csv, args.chart_output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
