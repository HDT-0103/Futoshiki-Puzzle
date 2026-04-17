from __future__ import annotations

from pathlib import Path

from Source.utils.chart_modules.common import plot_average_bar_chart


def render_runtime_chart(
    algorithms: list[str],
    summary: dict[str, dict[str, float]],
    chart_dir: Path,
    case_count: int,
) -> None:
    avg_runtime = [summary[a]["avg_runtime_s"] for a in algorithms]
    suffix = f"({case_count} Test Cases)" if case_count > 0 else ""
    plot_average_bar_chart(
        algorithms,
        avg_runtime,
        f"Average Runtime by Algorithm {suffix}".strip(),
        "Seconds (s)",
        "{:.3f} s",
        chart_dir / "avg_runtime_by_algorithm.png",
        use_symlog=True,
        symlog_linthresh=0.0001,
    )
