from __future__ import annotations

from pathlib import Path

from Source.utils.chart_modules.common import plot_average_bar_chart


def render_inferences_chart(
    algorithms: list[str],
    summary: dict[str, dict[str, float]],
    chart_dir: Path,
    case_count: int,
) -> None:
    avg_inferences = [summary[a]["avg_inferences"] for a in algorithms]
    suffix = f"({case_count} Test Cases)" if case_count > 0 else ""
    plot_average_bar_chart(
        algorithms,
        avg_inferences,
        f"Average Inferences by Algorithm {suffix}".strip(),
        "Count",
        "{:,.0f}",
        chart_dir / "avg_inferences_by_algorithm.png",
        use_symlog=True,
        symlog_linthresh=1.0,
    )
