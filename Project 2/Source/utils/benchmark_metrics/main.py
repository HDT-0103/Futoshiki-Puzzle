from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import tracemalloc
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Source.logic.stats import SolverStats
from Source.solvers.astar import solve_astar
from Source.solvers.backtracking import solve_bt
from Source.solvers.backward_chaining import solve_bc
from Source.solvers.bruteforce import solve_bf
from Source.solvers.forward_chaining import solve_fc
from Source.utils.benchmark_metrics import (
    compute_memory_mb,
    compute_runtime_s,
    resolve_expansions,
    resolve_inferences,
)
from Source.utils.chart_modules.main import generate_chart_pngs
from Source.utils.parser import parse_futoshiki_file

SOLVERS = {
    "fc": solve_fc,
    "bc": solve_bc,
    "astar": solve_astar,
    "bt": solve_bt,
    "bf": solve_bf,
}

DEFAULT_INPUTS_DIR = PROJECT_ROOT / "Inputs"
DEFAULT_BENCHMARK_DIR = PROJECT_ROOT / "Source" / "assets" / "benchmark"
DEFAULT_BENCHMARK_CSV = DEFAULT_BENCHMARK_DIR / "benchmark_result.csv"
DEFAULT_OUTPUTS_DIR = PROJECT_ROOT / "Outputs"


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def log(message: str) -> None:
    print(message, flush=True)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_float(row: dict[str, str], key: str) -> float:
    v = row.get(key, "")
    return 0.0 if v == "" else float(v)


def write_csv(path: Path, rows: list[dict[str, str | int | float]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def extract_solver_payload(result: object) -> tuple[object, object]:
    if isinstance(result, tuple):
        grid = result[0] if len(result) >= 1 else None
        payload = result[1] if len(result) >= 2 else None
        return grid, payload
    return result, None


def benchmark_one(input_path: Path, algo: str) -> tuple[dict[str, str | int | float], list[list[int]] | None]:
    instance = parse_futoshiki_file(input_path)
    stats = SolverStats(algorithm=algo)

    log(f"    [start] {input_path.name} | {algo} | size={instance.n}x{instance.n}")

    tracemalloc.start()
    start = time.perf_counter()

    solved = False
    inferences = 0
    expansions = 0
    grid: list[list[int]] | None = None
    try:
        solver = SOLVERS[algo]
        if algo == "astar":
            raw_result = solver(instance, stats=stats)
        else:
            raw_result = solver(instance)

        grid, solver_metric = extract_solver_payload(raw_result)
        inferences = resolve_inferences(algo, solver_metric, stats)
        expansions = resolve_expansions(algo, solver_metric, stats)
        solved = bool(grid)
    except Exception as ex:
        log(f"    [error] {input_path.name} | {algo} | {type(ex).__name__}: {ex}")
        solved = False
        inferences = resolve_inferences(algo, None, stats)
        expansions = resolve_expansions(algo, None, stats)

    elapsed_s = compute_runtime_s(start, time.perf_counter())
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed_mb = compute_memory_mb(peak_bytes)

    log(
        f"    [done ] {input_path.name} | {algo} | solved={solved} | "
        f"running_time_s={elapsed_s:.3f} | memory_usage_mb={elapsed_mb:.3f} | "
        f"inferences={inferences} | expansions={expansions}"
    )

    row = {
        "input_file": input_path.name,
        "algorithm": algo,
        "running_time_s": round(elapsed_s, 3),
        "memory_usage_mb": round(elapsed_mb, 3),
        "inferences": int(inferences),
        "expansions": int(expansions),
    }
    return row, grid


def _h_symbol(value: int) -> str:
    if value == 1:
        return "<"
    if value == -1:
        return ">"
    return " "


def _v_symbol(value: int) -> str:
    if value == 1:
        return "v"
    if value == -1:
        return "^"
    return " "


def format_output_text(instance, solved_grid: list[list[int]] | None) -> str:
    if not solved_grid:
        return "No solution\n"

    n = instance.n
    h = instance.h_constraints
    v = instance.v_constraints
    lines: list[str] = []

    for i in range(n):
        row_parts = [str(solved_grid[i][0])]
        for j in range(n - 1):
            row_parts.append(f" {_h_symbol(h[i][j])} ")
            row_parts.append(str(solved_grid[i][j + 1]))
        lines.append("".join(row_parts).rstrip())

        if i < n - 1:
            v_parts = [_v_symbol(v[i][0])]
            for j in range(1, n):
                v_parts.append("   ")
                v_parts.append(_v_symbol(v[i][j]))
            lines.append("".join(v_parts).rstrip())

    return "\n".join(lines).rstrip() + "\n"


def _output_file_name(input_path: Path) -> str:
    m = re.search(r"(\d+)", input_path.stem)
    if m:
        return f"output-{int(m.group(1)):02d}.txt"
    return f"output-{input_path.stem}.txt"


def write_formatted_outputs(
    input_files: list[Path],
    solved_by_input: dict[str, list[list[int]]],
    outputs_dir: Path,
) -> None:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    for input_path in input_files:
        instance = parse_futoshiki_file(input_path)
        solved_grid = solved_by_input.get(input_path.name)
        output_text = format_output_text(instance, solved_grid)
        output_path = outputs_dir / _output_file_name(input_path)
        output_path.write_text(output_text, encoding="utf-8")
        log(f"[output] wrote {output_path}")


def run_benchmark_from_files(
    input_files: list[Path],
    output_csv: Path,
    algorithms: list[str],
    outputs_dir: Path = DEFAULT_OUTPUTS_DIR,
) -> Path:
    if not input_files:
        raise FileNotFoundError("No input files were provided for benchmark")

    total_runs = len(input_files) * len(algorithms)
    log(f"[benchmark] start: {len(input_files)} testcases x {len(algorithms)} algorithms = {total_runs} runs")

    rows: list[dict[str, str | int | float]] = []
    solved_by_input: dict[str, list[list[int]]] = {}
    current_run = 0
    for input_path in input_files:
        log(f"[board] {input_path.name}")
        for algo in algorithms:
            current_run += 1
            log(f"  [progress] {current_run}/{total_runs}")
            row, solved_grid = benchmark_one(input_path, algo)
            rows.append(row)
            if solved_grid is not None and input_path.name not in solved_by_input:
                solved_by_input[input_path.name] = solved_grid

    fields = [
        "input_file",
        "algorithm",
        "running_time_s",
        "memory_usage_mb",
        "inferences",
        "expansions",
    ]
    write_csv(output_csv, rows, fields)
    write_formatted_outputs(input_files, solved_by_input, outputs_dir)
    log(f"[benchmark] completed: {len(rows)} rows written to {output_csv}")
    return output_csv


def run_benchmark(inputs_dir: Path, output_csv: Path, algorithms: list[str], outputs_dir: Path = DEFAULT_OUTPUTS_DIR) -> Path:
    input_files = sorted(inputs_dir.glob("input-*.txt"))
    if not input_files:
        raise FileNotFoundError(f"No input files found in {inputs_dir}")
    return run_benchmark_from_files(input_files, output_csv, algorithms, outputs_dir)


def run_benchmark_default_10(
    inputs_dir: Path,
    output_csv: Path,
    algorithms: list[str],
    outputs_dir: Path = DEFAULT_OUTPUTS_DIR,
) -> Path:
    input_files = [inputs_dir / f"input-{i:02d}.txt" for i in range(1, 11)]
    missing = [path.name for path in input_files if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing required test files in {inputs_dir}: {', '.join(missing)}"
        )
    log("[benchmark] using default 10 testcases: input-01.txt .. input-10.txt")
    return run_benchmark_from_files(input_files, output_csv, algorithms, outputs_dir)


def summarize_benchmark(benchmark_csv: Path) -> None:
    rows = read_rows(benchmark_csv)
    if not rows:
        raise ValueError("Benchmark CSV is empty")

    by_algo: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_algo[row["algorithm"]].append(row)

    algo_rows: list[dict[str, str | int | float]] = []
    for algo in sorted(by_algo):
        group = by_algo[algo]
        algo_rows.append(
            {
                "algorithm": algo,
                "cases": len(group),
                "avg_running_time_s": round(avg([to_float(r, "running_time_s") for r in group]), 3),
                "avg_memory_usage_mb": round(avg([to_float(r, "memory_usage_mb") for r in group]), 3),
                "avg_inferences": round(avg([to_float(r, "inferences") for r in group]), 3),
                "avg_expansions": round(avg([to_float(r, "expansions") for r in group]), 3),
            }
        )

    log("Benchmark summary (console only):")
    for r in algo_rows:
        log(
            f"- {r['algorithm']}: cases={r['cases']}, avg_running_time_s={r['avg_running_time_s']}, "
            f"avg_memory_usage_mb={r['avg_memory_usage_mb']}, avg_inferences={r['avg_inferences']}, "
            f"avg_expansions={r['avg_expansions']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified benchmark utility: run benchmark CSV and draw charts from that CSV.")
    parser.add_argument(
        "action",
        nargs="?",
        choices=["run", "run10", "summary", "charts", "all"],
        default="run10",
        help="Action to perform. Defaults to run10 when omitted.",
    )
    parser.add_argument("--inputs-dir", type=Path, default=DEFAULT_INPUTS_DIR)
    parser.add_argument("--benchmark-csv", type=Path, default=DEFAULT_BENCHMARK_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_BENCHMARK_DIR)
    parser.add_argument("--outputs-dir", type=Path, default=DEFAULT_OUTPUTS_DIR)
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=["fc", "bc", "astar", "bt", "bf"],
        choices=["fc", "bc", "astar", "bt", "bf"],
    )
    args = parser.parse_args()

    benchmark_ran = False
    if args.action in {"run", "all"}:
        run_benchmark(args.inputs_dir, args.benchmark_csv, args.algorithms, args.outputs_dir)
        benchmark_ran = True

    if args.action == "run10":
        run_benchmark_default_10(args.inputs_dir, args.benchmark_csv, args.algorithms, args.outputs_dir)
        benchmark_ran = True

    if args.action in {"summary", "all"}:
        summarize_benchmark(args.benchmark_csv)

    if args.action in {"charts", "all"}:
        generate_chart_pngs(args.benchmark_csv, args.output_dir)

    if benchmark_ran and args.action in {"run", "run10"}:
        log("[benchmark] generating charts from CSV...")
        generate_chart_pngs(args.benchmark_csv, args.output_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
