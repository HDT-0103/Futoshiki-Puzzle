from __future__ import annotations

from pathlib import Path

from Source.utils.chart_modules.common import plot_average_bar_chart


def render_memory_chart(
    algorithms: list[str],
    summary: dict[str, dict[str, float]],
    chart_dir: Path,
    case_count: int,
) -> None:
    _ = case_count
    avg_memory = [summary[a]["avg_memory_mb"] for a in algorithms]
    plot_average_bar_chart(
        algorithms,
        avg_memory,
        "Average Memory Usage",
        "Megabytes (MB)",
        "{:.3f} MB",
        chart_dir / "avg_memory_usage.png",
        use_symlog=True,
        symlog_linthresh=0.0001,
    )
