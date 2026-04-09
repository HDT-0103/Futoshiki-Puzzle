#!/usr/bin/env python3
from __future__ import annotations

import random
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUTS_DIR = PROJECT_ROOT / "Inputs"

# input-01.txt already exists. We generate input-02..input-10 with varied sizes.
PUZZLE_SPECS = [
    (2, 4, 7),
    (3, 5, 13),
    (4, 5, 29),
    (5, 6, 11),
    (6, 6, 31),
    (7, 7, 17),
    (8, 7, 37),
    (9, 9, 19),
    (10, 9, 41),
]


def latin_square(n: int, shift: int) -> list[list[int]]:
    return [[((r + c + shift) % n) + 1 for c in range(n)] for r in range(n)]


def build_puzzle(n: int, seed: int) -> tuple[list[list[int]], list[list[int]], list[list[int]]]:
    rng = random.Random(seed)
    solution = latin_square(n, shift=seed % n)

    # More clues for larger boards to keep runtime practical across all algorithms.
    clue_ratio = 0.60 if n >= 7 else 0.50
    clue_count = max(n, int(n * n * clue_ratio))

    all_cells = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(all_cells)
    clue_cells = set(all_cells[:clue_count])

    grid = [[solution[r][c] if (r, c) in clue_cells else 0 for c in range(n)] for r in range(n)]

    # Keep a moderate amount of inequalities.
    density = 0.35 if n <= 6 else 0.28
    h = [[0 for _ in range(n - 1)] for _ in range(n)]
    v = [[0 for _ in range(n)] for _ in range(n - 1)]

    for r in range(n):
        for c in range(n - 1):
            if rng.random() < density:
                h[r][c] = 1 if solution[r][c] < solution[r][c + 1] else -1

    for r in range(n - 1):
        for c in range(n):
            if rng.random() < density:
                v[r][c] = 1 if solution[r][c] < solution[r + 1][c] else -1

    return grid, h, v


def write_input(path: Path, n: int, grid: list[list[int]], h: list[list[int]], v: list[list[int]]) -> None:
    lines: list[str] = [str(n), "# Grid"]
    lines.extend(",".join(str(x) for x in row) for row in grid)
    lines.append("# Horizontal constraints")
    lines.extend(",".join(str(x) for x in row) for row in h)
    lines.append("# Vertical constraints")
    lines.extend(",".join(str(x) for x in row) for row in v)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    for idx, n, seed in PUZZLE_SPECS:
        grid, h, v = build_puzzle(n, seed)
        out_path = INPUTS_DIR / f"input-{idx:02d}.txt"
        write_input(out_path, n, grid, h, v)

    print("Generated input-02.txt .. input-10.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
