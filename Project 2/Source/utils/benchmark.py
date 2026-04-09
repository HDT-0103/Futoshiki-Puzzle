#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import time
import tracemalloc
from collections import defaultdict
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Source.logic.stats import SolverStats
from Source.solvers.astar import solve_astar
from Source.solvers.backtracking import solve_bt
from Source.solvers.backward_chaining import solve_bc
from Source.solvers.bruteforce import solve_bf
from Source.solvers.forward_chaining import solve_fc
from Source.utils.parser import parse_futoshiki_file

SOLVERS = {
    "fc": solve_fc,
    "bc": solve_bc,
    "astar": solve_astar,
    "bt": solve_bt,
    "bf": solve_bf,
}


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_float(row: dict[str, str], key: str) -> float:
    v = row.get(key, "")
    return 0.0 if v == "" else float(v)


def to_int(row: dict[str, str], key: str) -> int:
    v = row.get(key, "")
    return 0 if v == "" else int(float(v))


def write_csv(path: Path, rows: list[dict[str, str | int | float]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def benchmark_one(input_path: Path, algo: str) -> dict[str, str | int | float]:
    instance = parse_futoshiki_file(input_path)
    stats = SolverStats(algorithm=algo)

    tracemalloc.start()
    start = time.perf_counter()

    solved = False
    error_msg = ""
    try:
        grid = SOLVERS[algo](instance, stats=stats)
        solved = bool(grid)
    except Exception as ex:
        error_msg = str(ex)

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "input_file": input_path.name,
        "size": instance.n,
        "algorithm": algo,
        "solved": int(solved),
        "runtime_ms": round(elapsed_ms, 3),
        "peak_kb": round(peak_bytes / 1024.0, 3),
        "nodes_expanded": stats.nodes_expanded,
        "assignments_tried": stats.assignments_tried,
        "consistency_checks": stats.consistency_checks,
        "domain_reductions": stats.domain_reductions,
        "propagation_steps": stats.propagation_steps,
        "error": error_msg,
    }


def run_benchmark(inputs_dir: Path, output_csv: Path, algorithms: list[str]) -> Path:
    input_files = sorted(inputs_dir.glob("input-*.txt"))
    if not input_files:
        raise FileNotFoundError(f"No input files found in {inputs_dir}")

    rows: list[dict[str, str | int | float]] = []
    for input_path in input_files:
        for algo in algorithms:
            rows.append(benchmark_one(input_path, algo))

    fields = [
        "input_file",
        "size",
        "algorithm",
        "solved",
        "runtime_ms",
        "peak_kb",
        "nodes_expanded",
        "assignments_tried",
        "consistency_checks",
        "domain_reductions",
        "propagation_steps",
        "error",
    ]
    write_csv(output_csv, rows, fields)
    print(f"Benchmark completed: {len(rows)} rows written to {output_csv}")
    return output_csv


def summarize_benchmark(benchmark_csv: Path, inputs_dir: Path, output_dir: Path) -> None:
    rows = read_rows(benchmark_csv)
    if not rows:
        raise ValueError("Benchmark CSV is empty")

    by_algo: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_algo[row["algorithm"]].append(row)

    algo_rows: list[dict[str, str | int | float]] = []
    for algo in sorted(by_algo):
        group = by_algo[algo]
        solved_count = sum(to_int(r, "solved") for r in group)
        total = len(group)
        algo_rows.append(
            {
                "algorithm": algo,
                "cases": total,
                "solved_cases": solved_count,
                "success_rate_pct": round(100.0 * solved_count / total, 2),
                "avg_runtime_ms": round(avg([to_float(r, "runtime_ms") for r in group]), 3),
                "avg_peak_kb": round(avg([to_float(r, "peak_kb") for r in group]), 3),
                "avg_nodes_expanded": round(avg([to_float(r, "nodes_expanded") for r in group]), 3),
                "avg_assignments_tried": round(avg([to_float(r, "assignments_tried") for r in group]), 3),
                "avg_consistency_checks": round(avg([to_float(r, "consistency_checks") for r in group]), 3),
            }
        )

    by_size_algo: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_size_algo[(row["size"], row["algorithm"])].append(row)

    size_algo_rows: list[dict[str, str | int | float]] = []
    for (size, algo), group in sorted(by_size_algo.items(), key=lambda x: (int(x[0][0]), x[0][1])):
        size_algo_rows.append(
            {
                "size": size,
                "algorithm": algo,
                "cases": len(group),
                "avg_runtime_ms": round(avg([to_float(r, "runtime_ms") for r in group]), 3),
                "avg_peak_kb": round(avg([to_float(r, "peak_kb") for r in group]), 3),
                "avg_nodes_expanded": round(avg([to_float(r, "nodes_expanded") for r in group]), 3),
            }
        )

    input_profiles: list[dict[str, str | int]] = []
    for input_file in sorted(inputs_dir.glob("input-*.txt")):
        instance = parse_futoshiki_file(input_file)
        clues = sum(1 for row in instance.grid for v in row if v != 0)
        h_count = sum(1 for row in instance.h_constraints for v in row if v != 0)
        v_count = sum(1 for row in instance.v_constraints for v in row if v != 0)
        input_profiles.append(
            {
                "input_file": input_file.name,
                "size": f"{instance.n}x{instance.n}",
                "clues": clues,
                "ineq_constraints": h_count + v_count,
            }
        )

    print("Benchmark summary (console only):")
    for r in algo_rows:
        print(
            f"- {r['algorithm']}: cases={r['cases']}, solved={r['solved_cases']}, "
            f"success={r['success_rate_pct']}%, avg_runtime_ms={r['avg_runtime_ms']}, "
            f"avg_peak_kb={r['avg_peak_kb']}, avg_nodes={r['avg_nodes_expanded']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified benchmark utility: run and summarize benchmark results.")
    parser.add_argument("action", choices=["run", "summary", "all"], help="Action to perform.")
    parser.add_argument("--inputs-dir", type=Path, default=PROJECT_ROOT / "Inputs")
    parser.add_argument("--benchmark-csv", type=Path, default=PROJECT_ROOT / "assets" / "benchmark" / "benchmark_result.csv")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "assets" / "benchmark")
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=["fc", "bc", "astar", "bt", "bf"],
        choices=["fc", "bc", "astar", "bt", "bf"],
    )
    args = parser.parse_args()

    if args.action in {"run", "all"}:
        run_benchmark(args.inputs_dir, args.benchmark_csv, args.algorithms)

    if args.action in {"summary", "all"}:
        summarize_benchmark(args.benchmark_csv, args.inputs_dir, args.output_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
