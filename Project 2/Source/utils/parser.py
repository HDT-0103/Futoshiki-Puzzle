"""Input parser for Futoshiki puzzle instances.

Supported input styles:
- Comma-separated (official assignment format)
- Whitespace-separated

Constraint encoding:
- 0 = no constraint
- 1 = less-than (left < right or top < bottom)
- -1 = greater-than (left > right or top > bottom)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass(frozen=True)
class FutoshikiInstance:
    n: int
    grid: List[List[int]]
    h_constraints: List[List[int]]  # shape: n x (n-1), values in {-1, 0, 1}
    v_constraints: List[List[int]]  # shape: (n-1) x n, values in {-1, 0, 1}


def _tokenize_lines(text: str) -> List[List[str]]:
    lines: List[List[str]] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if "," in s:
            tokens = [tok.strip() for tok in s.split(",") if tok.strip()]
        else:
            tokens = s.split()
        lines.append(tokens)
    return lines


def _parse_int(token: str) -> int:
    if token in {".", "_", "x", "X"}:
        return 0
    return int(token)


def _parse_constraint_token(token: str) -> int:
    mapping = {
        "0": 0,
        "1": 1,
        "-1": -1,
        "<": 1,
        ">": -1,
    }
    if token not in mapping:
        raise ValueError(f"Invalid constraint token: {token}")
    return mapping[token]


def _expect_shape(rows: Sequence[Sequence[str]], expected_rows: int, expected_cols: int, name: str) -> None:
    if len(rows) != expected_rows:
        raise ValueError(f"{name}: expected {expected_rows} rows, got {len(rows)}")
    for i, r in enumerate(rows):
        if len(r) != expected_cols:
            raise ValueError(f"{name}: row {i} expected {expected_cols} cols, got {len(r)}")


def parse_futoshiki_file(path: Path) -> FutoshikiInstance:
    """
    Parse a Futoshiki input file into a structured instance.
    """
    text = Path(path).read_text(encoding="utf-8")
    lines = _tokenize_lines(text)
    if not lines:
        raise ValueError("Empty input file")

    n = int(lines[0][0])
    if n <= 1:
        raise ValueError(f"N must be >= 2, got {n}")

    idx = 1

    grid_tokens = lines[idx : idx + n]
    _expect_shape(grid_tokens, n, n, "grid")
    grid = [[_parse_int(tok) for tok in row] for row in grid_tokens]
    idx += n

    h_tokens = lines[idx : idx + n]
    _expect_shape(h_tokens, n, n - 1, "horizontal constraints")
    h_constraints = [[_parse_constraint_token(tok) for tok in row] for row in h_tokens]
    idx += n

    v_tokens = lines[idx : idx + (n - 1)]
    _expect_shape(v_tokens, n - 1, n, "vertical constraints")
    v_constraints = [[_parse_constraint_token(tok) for tok in row] for row in v_tokens]
    idx += n - 1

    if idx != len(lines):
        # Keep this strict so your solver doesn't silently misread malformed instances.
        raise ValueError(f"Unexpected trailing content: {len(lines) - idx} non-empty line(s) after vertical constraints.")

    return FutoshikiInstance(
        n=n,
        grid=grid,
        h_constraints=h_constraints,
        v_constraints=v_constraints,
    )

