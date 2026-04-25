"""Color palette and font definitions for the Futoshiki GUI."""
from __future__ import annotations

# Main font used throughout the UI. "Cascadia Code" falls back automatically
# on systems without it (Tkinter uses a system default).
FONT = "Cascadia Code"

# Full color palette — "Midnight Terminal" theme
PALETTE = dict(
    # Base backgrounds
    bg="#080b14",
    bg2="#0e1220",
    panel="#111730",
    panel2="#161e3a",

    # Grid cells
    cell="#1c2448",
    given="#301e68",
    solved="#0e3828",
    trying="#4a3808",
    fail="#481018",

    # Borders
    brd="#283060",
    brd_hi="#4050a0",

    # Numbers and text
    num="#d4d0f0",
    gnum="#c0a0ff",
    snum="#50ff90",
    tnum="#ffd050",
    fnum="#ff5060",
    domain="#484878",
    sign="#ff4848",

    # Labels
    lbl="#606088",
    title="#f0f0ff",
    sub="#9090b8",

    # Button accents
    accent="#5030b0", accent_h="#7050e0",
    green="#18884a",  green_h="#20bb60",
    orange="#b86018", orange_h="#e08030",
    red="#b02030",    red_h="#e03848",
    cyan="#1888a0",   cyan_h="#20b8d0",

    # Heatmap gradient
    heat=["#1c2448", "#2a3018", "#484008", "#785800", "#a84000", "#d82000"],

    # Chart
    chart_bg="#0c1028",
    tab_on="#2040a0",
    tab_off="#182040",

    # Per-solver colors
    scol={
        "Backtracking":      "#50ff90",
        "Brute Force":       "#ff5060",
        "Forward Chaining":  "#ffd050",
        "Backward Chaining": "#c0a0ff",
        "A* Search":         "#20d0e0",
        "Built-in BT":       "#50ff90",
    },
)

# Button hover map — used by widgets._btn
HOVER_MAP = {
    PALETTE["accent"]: PALETTE["accent_h"],
    PALETTE["green"]:  PALETTE["green_h"],
    PALETTE["orange"]: PALETTE["orange_h"],
    PALETTE["red"]:    PALETTE["red_h"],
    PALETTE["cyan"]:   PALETTE["cyan_h"],
}
