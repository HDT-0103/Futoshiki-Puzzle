# GUI Module Structure

Refactored from a single 1061-line `gui.py` into 10 focused modules.
Total ~1660 lines but each file ≤ 700 lines and has a single clear responsibility.

## Files

| File | Lines | Responsibility |
|------|-------|----------------|
| `__init__.py` | 4 | Package marker, exposes `main()` |
| `gui.py` | 12 | Backward-compat shim for old `main.py` import path |
| `metrics.py` | 39 | Solver result normalization (`unpack()`) |
| `widgets.py` | 55 | UI atoms: `section_header`, `separator`, `label_button`, `action_button` |
| `theme.py` | 74 | Color palette + font + hover map |
| `chart.py` | 119 | Performance chart drawing on Tkinter canvas |
| `solvers_loader.py` | 136 | Solver registry + animated backtracking |
| `grid_view.py` | 185 | Puzzle grid rendering + domain calculation |
| `exporter.py` | 344 | Save solution / Export log / Export charts |
| `app.py` | 696 | Main `App` class — UI orchestration + event handlers |

## Installation

Replace the contents of `Source/gui/` with these files:

```
Source/gui/
├── __init__.py
├── app.py
├── chart.py
├── exporter.py
├── grid_view.py
├── gui.py
├── metrics.py
├── solvers_loader.py
├── theme.py
└── widgets.py
```

`main.py` doesn't need to change — the import path
`from Source.gui.gui import main as gui_main` still works.

## Architecture

```
                      ┌──────────────┐
                      │   app.py     │  ← user events + state
                      │  (App class) │
                      └──────┬───────┘
                             │ delegates to:
        ┌────────┬───────────┼───────────┬────────────┐
        ▼        ▼           ▼           ▼            ▼
   ┌──────┐ ┌────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
   │theme │ │widgets │ │grid_view │ │  chart  │ │ exporter │
   └──────┘ └────────┘ └──────────┘ └─────────┘ └──────────┘
        ▲        ▲           ▲           ▲            ▲
        └────────┴───────────┴───────────┴────────────┘
                             │
                       Pure functions
                       (no shared state)

   ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
   │  metrics.py  │  │solvers_loader│  │  parser (utils) │
   │   unpack()   │  │  SOLVERS{}   │  │ parse_futoshiki │
   └──────────────┘  └──────────────┘  └─────────────────┘
```

## Design principles

- **theme.py** has zero imports — palette is just data.
- **widgets.py** depends only on theme.
- **grid_view.py**, **chart.py** are stateless pure renderers — receive state as args, write to canvas.
- **exporter.py** owns all file I/O — keeps app.py free of `csv`/`matplotlib`/`filedialog` clutter.
- **app.py** is the only file that manages mutable state and threading.
- **solvers_loader.py** owns dynamic solver discovery + animation thread logic.
- **metrics.py** is the single source of truth for normalizing solver return values.
