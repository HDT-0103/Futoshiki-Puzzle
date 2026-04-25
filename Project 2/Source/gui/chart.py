"""Performance chart rendering.

Draws a bar chart of comparison results onto a Tkinter canvas.
Supports four metrics: time, memory, inferences, expansions.
Gracefully handles missing data, timeouts, and N/A solver states.
"""
from __future__ import annotations
import tkinter as tk

from Source.gui.theme import PALETTE as P, FONT


def _get_metric_value(info: dict, metric: str) -> int | float | None:
    """Extract a metric from a result entry, tolerating legacy formats."""
    if not info.get("ok"):
        return None

    if metric in ("inferences", "expansions"):
        v = info.get(metric)
        if v is not None:
            return int(v)
        # Fallback: old format where "steps" held a dict
        steps = info.get("steps")
        if isinstance(steps, dict):
            return int(steps.get(metric, 0))
        if isinstance(steps, (int, float)):
            return int(steps)
        return 0

    return info.get(metric, 0)


def draw_chart(canvas: tk.Canvas, cmp: dict, metric: str) -> None:
    """Draw a comparison bar chart for the selected metric."""
    canvas.delete("all")
    cw = canvas.winfo_width() or 380
    ch = canvas.winfo_height() or 200

    if not cmp:
        canvas.create_text(cw // 2, ch // 2,
                           text="Run Solve or Compare All\nto see results",
                           font=(FONT, 9), fill=P["lbl"], justify="center")
        return

    unit = {"time": "s", "mem": "KB",
            "inferences": "", "expansions": ""}.get(metric, "")

    names = list(cmp.keys())
    if not names:
        return

    pad_l, pad_r, pad_t, pad_b = 55, 15, 12, 30
    area_w = cw - pad_l - pad_r
    area_h = ch - pad_t - pad_b
    group_w = area_w / len(names)
    bar_w = max(group_w * 0.5, 14)

    # Collect values
    vals = [_get_metric_value(cmp[nm], metric) for nm in names]
    ok_vals = [v for v in vals if v is not None]

    if not ok_vals:
        canvas.create_text(cw // 2, ch // 2,
                           text="No data for this metric",
                           font=(FONT, 9), fill=P["lbl"])
        return

    mx = max(ok_vals) or 0.001

    # Y-axis grid lines
    for i in range(5):
        yy = pad_t + int(area_h * i / 4)
        canvas.create_line(pad_l, yy, cw - pad_r, yy,
                           fill=P["brd"], dash=(2, 4))
        lv = mx * (1 - i / 4)
        if metric == "time":
            txt = f"{lv:.4f}"
        elif metric == "mem":
            txt = f"{lv:.1f}"
        else:
            txt = f"{int(lv)}"
        canvas.create_text(pad_l - 6, yy, text=txt,
                           font=(FONT, 6), fill=P["lbl"], anchor="e")

    # Bars
    for idx, nm in enumerate(names):
        x_center = pad_l + idx * group_w + group_w / 2
        info = cmp[nm]
        color = P["scol"].get(nm, "#888888")
        v = vals[idx]

        if v is not None and info.get("ok"):
            bh = max((v / mx) * area_h, 4)
            x = x_center - bar_w / 2
            y = pad_t + area_h - bh

            canvas.create_rectangle(x, y, x + bar_w, pad_t + area_h,
                                    fill=color, outline="")
            canvas.create_rectangle(x, y, x + bar_w, y + 2,
                                    fill="#ffffff", outline="",
                                    stipple="gray25")
            if metric == "time":
                label = f"{v:.4f}{unit}"
            elif metric == "mem":
                label = f"{v:.1f}{unit}"
            else:
                label = f"{int(v)}"
            canvas.create_text(x_center, y - 9, text=label,
                               font=(FONT, 7, "bold"), fill=color)
        elif info.get("note") == "timeout":
            canvas.create_text(x_center, pad_t + area_h - 16,
                               text="TIMEOUT", font=(FONT, 7, "bold"),
                               fill=P["orange_h"])
        else:
            canvas.create_text(x_center, pad_t + area_h - 16,
                               text="N/A", font=(FONT, 8), fill=P["lbl"])

        canvas.create_text(x_center, pad_t + area_h + 14,
                           text=nm[:14], font=(FONT, 7), fill=P["sub"])
