# Project 2: Logic - Futoshiki Puzzles (CSC14003)

## Overview
This project solves Futoshiki puzzles with multiple AI approaches required by the assignment:
- Forward Chaining (`fc`)
- Backward Chaining (`bc`)
- A* Search (`astar`)
- Backtracking (`bt`)
- Brute Force (`bf`)

It also includes automatic grounded KB/CNF generation in `Source/logic/kb.py`.

## Input Format
Each input file follows:
1. First line: `N`
2. Next `N` lines: grid values (`0` for empty)
3. Next `N` lines: horizontal constraints (`N-1` values each)
4. Next `N-1` lines: vertical constraints (`N` values each)

Constraint values:
- `0`: no constraint
- `1`: less-than (`<`)
- `-1`: greater-than (`>`)

Both comma-separated and whitespace-separated formats are supported.

## Run
From the project root:

```bash
python -m Source.main Inputs/input-01.txt -a bt -o Outputs/output-01.txt
```

Available algorithms (`-a`):
- `fc`
- `bc`
- `astar`
- `bt`
- `bf`

## Generate Additional Inputs
Generate `input-02.txt` to `input-10.txt` (sizes: 4x4, 5x5, 6x6, 7x7, 9x9):

```bash
python scripts/generate_additional_puzzles.py
```

## Benchmark to CSV
Run all algorithms on all input files and export metrics:

```bash
python util/benchmark.py run --benchmark-csv Outputs/benchmark_results.csv
```

CSV columns:
- `input_file`, `size`, `algorithm`, `solved`
- `runtime_ms`, `peak_kb`
- `nodes_expanded`, `assignments_tried`
- `consistency_checks`, `domain_reductions`, `propagation_steps`
- `error`

## Summarize Benchmarks for Report
Generate aggregate tables and input profile:

```bash
python util/benchmark.py summary
```

Generated files:
- `Outputs/benchmark_summary_by_algorithm.csv`
- `Outputs/benchmark_summary_by_size_algorithm.csv`
- `Outputs/input_profile.csv`
- `Outputs/benchmark_summary.md`

## Generate Mermaid Charts for Report
Create chart blocks (runtime/memory/nodes vs size):

```bash
python util/benchmark.py charts
```

Generated file:
- `assets/benchmark/benchmark_charts_mermaid.md`

## Run Full Benchmark Pipeline
Run benchmark + summary + charts in one command:

```bash
python util/benchmark.py all
```

## Output
The output contains the solved grid while preserving inequality signs:
- Horizontal: `<` and `>`
- Vertical: `v` (top < bottom), `^` (top > bottom)

## Files
- `Source/main.py`: CLI entrypoint and output formatter
- `Source/utils/parser.py`: parser for assignment input format
- `Source/logic/constraints.py`: shared CSP constraints and propagation
- `Source/logic/stats.py`: solver statistics counters for benchmarking
- `Source/logic/kb.py`: grounded KB and CNF-style clause generation
- `Source/solvers/`: all solver implementations
- `scripts/generate_additional_puzzles.py`: auto-generate 9 additional valid puzzles
- `util/benchmark.py`: unified benchmark runner (run, summary, charts, all)
- `assets/benchmark/`: benchmark chart assets for the report
- `Report_Skeleton.md`: report template with FOL/CNF/experiment sections

## Sample
`Inputs/input-01.txt` is a runnable 4x4 sample puzzle.

