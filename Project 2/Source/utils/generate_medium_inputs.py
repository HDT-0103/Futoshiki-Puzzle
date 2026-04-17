from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUTS_DIR = PROJECT_ROOT / "Inputs"


@dataclass(frozen=True)
class PuzzleSpec:
    filename: str
    size: int
    clue_ratio: float
    constraint_ratio: float
    min_clues_per_row: int = 1


SPECS: list[PuzzleSpec] = [
    PuzzleSpec("input-05.txt", 6, clue_ratio=0.32, constraint_ratio=0.62),
    PuzzleSpec("input-06.txt", 6, clue_ratio=0.30, constraint_ratio=0.58),
    PuzzleSpec("input-07.txt", 7, clue_ratio=0.26, constraint_ratio=0.58),
    PuzzleSpec("input-08.txt", 7, clue_ratio=0.24, constraint_ratio=0.55),
    PuzzleSpec("input-09.txt", 9, clue_ratio=0.20, constraint_ratio=0.52),
    PuzzleSpec("input-10.txt", 9, clue_ratio=0.18, constraint_ratio=0.50),
]


def _latin_square(size: int, rng: random.Random) -> list[list[int]]:
    base = [[(r + c) % size + 1 for c in range(size)] for r in range(size)]

    row_perm = list(range(size))
    col_perm = list(range(size))
    val_perm = list(range(1, size + 1))
    rng.shuffle(row_perm)
    rng.shuffle(col_perm)
    rng.shuffle(val_perm)

    transformed = [[val_perm[base[row_perm[r]][col_perm[c]] - 1] for c in range(size)] for r in range(size)]
    return transformed


def _pick_givens(solution: list[list[int]], spec: PuzzleSpec, rng: random.Random) -> list[list[int]]:
    size = spec.size
    total_cells = size * size
    target = max(size + 2, int(round(total_cells * spec.clue_ratio)))

    givens = [[0 for _ in range(size)] for _ in range(size)]
    chosen: set[tuple[int, int]] = set()

    # Ensure at least one clue in each row first.
    for r in range(size):
        c = rng.randrange(size)
        chosen.add((r, c))

    # Fill remaining clues randomly.
    all_cells = [(r, c) for r in range(size) for c in range(size)]
    rng.shuffle(all_cells)
    for cell in all_cells:
        if len(chosen) >= target:
            break
        chosen.add(cell)

    for r, c in chosen:
        givens[r][c] = solution[r][c]

    return givens


def _scale_for_hardness(base_ratio: float, hardness_multiplier: float, *, kind: str) -> float:
    """
    Scale generator density by hardness.

    - clue ratio drops strongly when hardness increases
    - constraint ratio drops moderately when hardness increases
    """
    if hardness_multiplier <= 0:
        raise ValueError("hardness_multiplier must be > 0")

    if hardness_multiplier == 1.0:
        return base_ratio

    if kind == "clue":
        scaled = base_ratio / hardness_multiplier
        if hardness_multiplier > 1.0:
            return max(0.10, scaled)
        return min(0.75, scaled)

    # kind == "constraint"
    scaled = base_ratio / (hardness_multiplier ** 0.5)
    if hardness_multiplier > 1.0:
        return max(0.25, scaled)
    return min(0.95, scaled)


def _build_constraints(solution: list[list[int]], spec: PuzzleSpec, rng: random.Random) -> tuple[list[list[int]], list[list[int]]]:
    size = spec.size
    h = [[0 for _ in range(size - 1)] for _ in range(size)]
    v = [[0 for _ in range(size)] for _ in range(size - 1)]

    for r in range(size):
        for c in range(size - 1):
            if rng.random() <= spec.constraint_ratio:
                left = solution[r][c]
                right = solution[r][c + 1]
                h[r][c] = 1 if left < right else -1

    for r in range(size - 1):
        for c in range(size):
            if rng.random() <= spec.constraint_ratio:
                top = solution[r][c]
                bottom = solution[r + 1][c]
                v[r][c] = 1 if top < bottom else -1

    return h, v


def _format_matrix(rows: Iterable[Iterable[int]]) -> str:
    return "\n".join(",".join(str(v) for v in row) for row in rows)


def _write_instance(path: Path, size: int, grid: list[list[int]], h: list[list[int]], v: list[list[int]]) -> None:
    lines = [str(size), _format_matrix(grid), _format_matrix(h), _format_matrix(v)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_medium_inputs(
    inputs_dir: Path,
    seed: int | None = None,
    hardness_multiplier: float = 1.0,
    only_files: set[str] | None = None,
) -> list[Path]:
    inputs_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    written: list[Path] = []

    for spec in SPECS:
        if only_files is not None and spec.filename not in only_files:
            continue

        tuned_spec = PuzzleSpec(
            filename=spec.filename,
            size=spec.size,
            clue_ratio=_scale_for_hardness(spec.clue_ratio, hardness_multiplier, kind="clue"),
            constraint_ratio=_scale_for_hardness(spec.constraint_ratio, hardness_multiplier, kind="constraint"),
            min_clues_per_row=spec.min_clues_per_row,
        )
        solution = _latin_square(spec.size, rng)
        grid = _pick_givens(solution, tuned_spec, rng)
        h, v = _build_constraints(solution, tuned_spec, rng)
        path = inputs_dir / spec.filename
        _write_instance(path, tuned_spec.size, grid, h, v)
        written.append(path)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate medium-difficulty Futoshiki input files.")
    parser.add_argument("--inputs-dir", type=Path, default=DEFAULT_INPUTS_DIR)
    parser.add_argument("--seed", type=int, default=20260417)
    parser.add_argument("--hardness-multiplier", type=float, default=1.0)
    parser.add_argument("--only", nargs="+", help="Optional file names to regenerate, e.g. input-07.txt input-08.txt")
    args = parser.parse_args()

    only_files = set(args.only) if args.only else None
    written = generate_medium_inputs(args.inputs_dir, args.seed, args.hardness_multiplier, only_files)
    for path in written:
        print(f"Wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())