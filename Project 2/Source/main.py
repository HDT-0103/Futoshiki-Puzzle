#!/usr/bin/env python3
"""
CSC14003 - Project 2: Logic - Futoshiki Puzzles

Entry point for running different solving strategies (FC/BC/A*/Backtracking).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from Source.utils.parser import parse_futoshiki_file


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="futoshiki",
        description="Solve Futoshiki puzzles using logic/search-based algorithms.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to an input file (e.g., Inputs/input-01.txt).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional output path. If omitted, prints to stdout.",
    )
    parser.add_argument(
        "-a",
        "--algorithm",
        required=True,
        choices=["fc", "bc", "astar", "bt"],
        help="Algorithm: fc (Forward Chaining), bc (Backward Chaining), astar (A*), bt (Backtracking).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug prints (minimal; expand as needed).",
    )
    return parser


def solve(instance, algorithm: str):
    """
    Dispatch to the chosen solver.

    Expected return value: a solved grid as List[List[int]] (or a richer result object),
    depending on your team design.
    """
    if algorithm == "fc":
        from Source.solvers.forward_chaining import solve_fc

        return solve_fc(instance)
    if algorithm == "bc":
        from Source.solvers.backward_chaining import solve_bc

        return solve_bc(instance)
    if algorithm == "astar":
        from Source.solvers.astar import solve_astar

        return solve_astar(instance)
    if algorithm == "bt":
        from Source.solvers.backtracking import solve_bt

        return solve_bt(instance)

    raise ValueError(f"Unknown algorithm: {algorithm}")


def format_solution_grid(grid) -> str:
    return "\n".join(" ".join(str(v) for v in row) for row in grid) + "\n"


def write_output(text: str, output_path: Optional[Path]) -> None:
    if output_path is None:
        sys.stdout.write(text)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.debug:
        print(f"[debug] input={args.input} algorithm={args.algorithm} output={args.output}")

    instance = parse_futoshiki_file(args.input)
    solution = solve(instance, args.algorithm)

    # For now, solvers return a grid-like structure; adjust as your implementation evolves.
    out_text = format_solution_grid(solution)
    write_output(out_text, args.output)
    return 0


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        from Source.gui import main as gui_main
        gui_main()
    else:
        raise SystemExit(main())