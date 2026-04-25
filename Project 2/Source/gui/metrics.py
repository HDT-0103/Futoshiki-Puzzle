"""Solver result normalization.

All 5 solvers should return a 3-tuple `(grid, metrics, logs)` where
`metrics` is a dict with `inferences` and `expansions` keys. This module
provides a single `unpack()` function that tolerates older formats
(2-tuples, int metrics, raw grids) for backward compatibility.
"""
from __future__ import annotations
from typing import Any


def unpack(result_data: Any) -> tuple[Any, dict[str, int], list[str]]:
    """Normalize any solver return value to `(grid, metrics_dict, logs)`.

    Accepted input formats:
      - `grid` (list of lists)
      - `(grid, metrics)` where metrics is int or dict
      - `(grid, metrics, logs)` — preferred format
    """
    if not isinstance(result_data, tuple):
        return result_data, {"inferences": 0, "expansions": 0}, []

    if len(result_data) >= 3:
        grid, metrics, logs = result_data[0], result_data[1], result_data[2]
    elif len(result_data) == 2:
        grid, metrics, logs = result_data[0], result_data[1], []
    else:
        grid, metrics, logs = result_data[0], 0, []

    # Normalize metrics to a well-formed dict
    if isinstance(metrics, (int, float)):
        metrics = {"inferences": int(metrics), "expansions": int(metrics)}
    elif not isinstance(metrics, dict):
        metrics = {"inferences": 0, "expansions": 0}

    metrics.setdefault("inferences", 0)
    metrics.setdefault("expansions", 0)

    return grid, metrics, logs
