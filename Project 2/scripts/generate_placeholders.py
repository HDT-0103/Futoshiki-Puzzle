#!/usr/bin/env python3
"""
Generate placeholder input files for the assignment.

Creates `Inputs/input-01.txt` ... `Inputs/input-10.txt` as empty files by default.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate placeholder Inputs files.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root containing the Inputs/ folder.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of placeholder files to create (default: 10).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files (default: skip existing).",
    )
    args = parser.parse_args()

    inputs_dir = args.root / "Inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0
    for i in range(1, args.count + 1):
        p = inputs_dir / f"input-{i:02d}.txt"
        if p.exists() and not args.force:
            skipped += 1
            continue
        p.write_text("", encoding="utf-8")
        created += 1

    print(f"Created {created} file(s), skipped {skipped} existing file(s) in {inputs_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

