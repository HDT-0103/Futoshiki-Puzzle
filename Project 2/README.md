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
## Setup

### 1) Clone repo
```bash
git clone https://github.com/HDT-0103/Futoshiki-Puzzle.git
cd Futoshiki-Puzzle
```

### 2) Create and activate a virtual environment (venv)

**Windows (PowerShell):**
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```bash
python -m venv .venv
.\.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

> If PowerShell blocks script execution on Windows, run:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

### 3) Install dependencies from requirements.txt
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Run the project
From the project root, run:
```bash
python main.py
```
This opens the GUI. Choose puzzle file and algorithm inside the interface.

### 5) Deactivate the virtual environment (when needed)
```bash
deactivate
```

## Generate Additional Inputs
Generate `input-02.txt` to `input-10.txt` (sizes: 4x4, 5x5, 6x6, 7x7, 9x9):

```bash
python scripts/generate_additional_puzzles.py
```

## Benchmark to CSV
Run all algorithms on all input files and export metrics:

```bash
python Source/utils/benchmark.py run --benchmark-csv Source/assets/benchmark/benchmark_result.csv
```

Run exactly the assignment test set (`input-01.txt` to `input-10.txt`) with one command:

```bash
python Source/utils/benchmark.py run10 --benchmark-csv Source/assets/benchmark/benchmark_result.csv
```

CSV columns:
- `input_file`, `size`, `algorithm`, `solved`
- `runtime_ms` (running time)
- `peak_kb` (memory usage)
- `nodes_expanded` (number of inferences/expansions)

This is the only CSV file used as source for visualization.

## Summarize Benchmarks (Console Only)
Print aggregate metrics to terminal without creating extra files:

```bash
python Source/utils/benchmark.py summary
```

## Generate Charts and Table Images
Create chart images and rendered table images directly from the benchmark CSV:

```bash
python Source/utils/benchmark.py charts
```

Generated file:
- `Source/assets/benchmark/runtime_comparison.png`
- `Source/assets/benchmark/memory_comparison.png`
- `Source/assets/benchmark/nodes_comparison.png`
- `Source/assets/benchmark/runtime_by_case.png`
- `Source/assets/benchmark/memory_by_case.png`
- `Source/assets/benchmark/expansions_by_case.png`
- `Source/assets/benchmark/table_algorithm_summary.png`
- `Source/assets/benchmark/table_case_by_case.png`

## Run Full Benchmark Pipeline
Run benchmark + summary + charts in one command:

```bash
python Source/utils/benchmark.py all
```

## Output
The output contains the solved grid while preserving inequality signs:
- Horizontal: `<` and `>`
- Vertical: `v` (top < bottom), `^` (top > bottom)

## A* Heuristic Proof (Admissible + Consistent)
We use:

- State potential $U(s)$ = number of currently unassigned cells (domain size > 1).
- Heuristic $h(s) = U(s)$.
- Transition cost $c(s,s') = U(s) - U(s')$ after assigning one value and AC-3 style propagation (`reduce_domains`).

Because propagation only shrinks domains, we have $U(s') < U(s)$ for every valid expansion, so
$c(s,s') > 0$.

### Admissible
For any path $s = s_0 \to s_1 \to ... \to s_k = goal$:

$$
\sum_{i=0}^{k-1} c(s_i,s_{i+1})
= \sum_{i=0}^{k-1} (U(s_i)-U(s_{i+1}))
= U(s)-U(goal)
= U(s)
= h(s)
$$

So $h(s)$ equals the true remaining path cost under this cost model, therefore it is admissible.

### Consistent
For any edge $s \to s'$:

$$
h(s) = U(s) = (U(s)-U(s')) + U(s') = c(s,s') + h(s')
$$

Hence $h(s) \le c(s,s') + h(s')$ holds with equality for all transitions, so the heuristic is consistent.

### Implementation Invariant Used by A*
The solver keeps the invariant:

$$
g(s) = U(s_0) - U(s)
$$

where $s_0$ is the initial reduced state.
So for each child $s'$ generated from $s$:

$$
g(s') = g(s) + c(s,s')
$$

and

$$
f(s) = g(s) + h(s) = U(s_0)
$$

which is constant over all reachable states under this model.

### Where It Is Implemented
- Heuristic $h(s)$: `_heuristic(domains)` in `Source/solvers/astar.py`.
- AC-3 style propagation: `reduce_domains` in `Source/logic/constraints.py`.
- A* cost model $c(s,s')$: `_progress_cost(parent, child)` in `Source/solvers/astar.py`.
- Invariant check: `g2 = initial_u - child_u` and consistency guard in `Source/solvers/astar.py`.

## Files
- `main.py`: single project entrypoint (opens GUI)
- `Source/gui/gui.py`: GUI implementation
- `Source/utils/parser.py`: parser for assignment input format
- `Source/logic/constraints.py`: shared CSP constraints and propagation
- `Source/logic/stats.py`: solver statistics counters for benchmarking
- `Source/logic/kb.py`: grounded KB and CNF-style clause generation
- `Source/solvers/`: all solver implementations
- `scripts/generate_additional_puzzles.py`: auto-generate 9 additional valid puzzles
- `Source/utils/benchmark.py`: unified benchmark runner (run, summary, all)
- `assets/benchmark/`: benchmark chart assets for the report
- `Report_Skeleton.md`: report template with FOL/CNF/experiment sections

## Sample
`Inputs/input-01.txt` is a runnable 4x4 sample puzzle.

