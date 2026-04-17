from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from Source.utils.chart_modules.common import AX_BG, FIG_BG, algo_display_name


BEST_COLOR = "#dcefd5"
MID_COLOR = "#f4e7c7"
WORST_COLOR = "#f1d3d0"
HEADER_COLOR = "#2d5a88"
HEADER_TEXT_COLOR = "#ffffff"
ROW_LABEL_COLOR = "#d9d9d9"
BORDER_COLOR = "#b8b8b8"
TEXT_COLOR = "#232323"


def _row_colors(values: list[float], *, lower_is_better: bool) -> list[str]:
    total = len(values)
    if total <= 1:
        return [BEST_COLOR for _ in values]

    order = sorted(range(total), key=lambda i: values[i], reverse=not lower_is_better)
    colors = [MID_COLOR for _ in values]

    best_count = max(1, round(total * 0.25))
    worst_count = max(1, round(total * 0.25))
    if best_count + worst_count > total:
        worst_count = max(1, total - best_count)

    for position, index in enumerate(order):
        if position < best_count:
            colors[index] = BEST_COLOR
        elif position >= total - worst_count:
            colors[index] = WORST_COLOR

    return colors


def _format_value(metric: str, value: float) -> str:
    if metric in {"runtime", "memory"}:
        return f"{value:.2f}"
    return f"{value:,.0f}"


def render_summary_table_4features(
    algorithms: list[str],
    summary: dict[str, dict[str, float]],
    chart_dir: Path,
    case_count: int,
) -> None:
    _ = case_count
    if not algorithms:
        return

    metrics = [
        ("Runtime (avg)", [summary[a]["avg_runtime_s"] for a in algorithms], True, "runtime"),
        ("Memory (avg)", [summary[a]["avg_memory_mb"] for a in algorithms], True, "memory"),
        ("Inferences (avg)", [summary[a]["avg_inferences"] for a in algorithms], True, "count"),
        ("Expansions (avg)", [summary[a]["avg_expansions"] for a in algorithms], True, "count"),
    ]

    fig, ax = plt.subplots(figsize=(10.4, 0.98 + 0.62 * (len(metrics) + 1)), dpi=180)
    fig.patch.set_facecolor(FIG_BG)
    ax.set_facecolor(AX_BG)
    ax.axis("off")

    columns = ["Metric"] + [algo_display_name(algo) for algo in algorithms]
    table_rows: list[list[str]] = []
    cell_colours: list[list[str]] = []

    cell_colours.append([HEADER_COLOR] * len(columns))

    for metric_label, values, lower_is_better, metric_kind in metrics:
        row_values = [metric_label]
        row_colours = [ROW_LABEL_COLOR]
        colors = _row_colors(values, lower_is_better=lower_is_better)
        for index, value in enumerate(values):
            row_values.append(_format_value(metric_kind, value))
            row_colours.append(colors[index])
        table_rows.append(row_values)
        cell_colours.append(row_colours)

    table = ax.table(
        cellText=[columns] + table_rows,
        cellColours=cell_colours,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10.5)
    table.scale(1, 1.8)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(BORDER_COLOR)
        cell.set_linewidth(0.8)
        cell.get_text().set_color(TEXT_COLOR)
        if row == 0:
            cell.get_text().set_fontweight("bold")
            cell.get_text().set_color(HEADER_TEXT_COLOR)
            cell.set_height(cell.get_height() * 1.15)
        if col == 0 and row > 0:
            cell.get_text().set_fontweight("bold")

    ax.set_title("Summary of Average Performance Across All Metrics", fontsize=13.5, fontweight="bold", pad=12)
    ax.text(
        0.5,
        1.03,
        "Green = best, Yellow = middle, Red = worst",
        ha="center",
        va="bottom",
        transform=ax.transAxes,
        fontsize=10,
        color="#404040",
    )

    output_path = chart_dir / "summary_table_4features.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, facecolor=FIG_BG)
    plt.close(fig)
    print(f"Wrote: {output_path}")