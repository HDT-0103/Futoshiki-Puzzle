from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt

from Source.utils.chart_modules.common import AX_BG, FIG_BG, GRID_COLOR, algo_radar_label, rank_scores


def render_overview_chart(
    algorithms: list[str],
    summary: dict[str, dict[str, float]],
    chart_dir: Path,
    case_count: int,
) -> None:
    _ = case_count
    if not algorithms:
        return

    runtimes = [summary[a]["avg_runtime_s"] for a in algorithms]
    memories = [summary[a]["avg_memory_mb"] for a in algorithms]
    inferences = [summary[a]["avg_inferences"] for a in algorithms]
    expansions = [summary[a]["avg_expansions"] for a in algorithms]

    runtime_scores = rank_scores(runtimes, lower_is_better=True)
    memory_scores = rank_scores(memories, lower_is_better=True)
    inference_scores = rank_scores(inferences, lower_is_better=True)
    expansion_scores = rank_scores(expansions, lower_is_better=True)

    categories = ["Running Time", "Memory Usage", "Inferences", "Expansions"]
    angle_step = 2.0 * math.pi / len(categories)
    angles = [i * angle_step for i in range(len(categories))]
    angles_closed = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(8.2, 5.4), subplot_kw={"polar": True}, dpi=180)
    fig.patch.set_facecolor(FIG_BG)
    ax.set_facecolor(AX_BG)

    palette = ["#5ea5f5", "#cf9a43", "#72b86a", "#7d73e6", "#6b7d8f", "#d783bc", "#44b8cf"]

    for i, algo in enumerate(algorithms):
        values = [runtime_scores[i], memory_scores[i], inference_scores[i], expansion_scores[i]]
        values_closed = values + [values[0]]
        color = palette[i % len(palette)]
        ax.plot(
            angles_closed,
            values_closed,
            linewidth=2.0,
            color=color,
            label=algo_radar_label(algo),
            marker="o",
            ms=3,
        )
        ax.fill(angles_closed, values_closed, color=color, alpha=0.08)

    ax.set_title("Overview Performance Radar", fontsize=12, fontweight="bold", pad=6)
    ax.set_theta_offset(math.pi / 2.0)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles)
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_ylim(0.0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels([])
    ax.spines["polar"].set_color("#b7bcc6")
    ax.spines["polar"].set_linewidth(0.85)
    ax.grid(color=GRID_COLOR, alpha=0.6)

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=min(5, len(algorithms)),
        frameon=False,
        fontsize=8,
    )

    output_path = chart_dir / "overview_performance_radar.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, facecolor=FIG_BG)
    plt.close(fig)
    print(f"Wrote: {output_path}")
