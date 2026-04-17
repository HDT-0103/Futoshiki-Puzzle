from __future__ import annotations


def compute_memory_mb(peak_bytes: int) -> float:
    return peak_bytes / (1024.0 * 1024.0)
