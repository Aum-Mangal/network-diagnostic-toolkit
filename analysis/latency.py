"""
latency.py — Latency analysis helpers.
"""
from __future__ import annotations
from typing import List, Optional


def classify_latency(ms: float) -> str:
    """Return a human-readable quality label for a latency value."""
    if ms <= 30:
        return "Excellent"
    elif ms <= 80:
        return "Good"
    elif ms <= 150:
        return "Fair"
    elif ms <= 300:
        return "Poor"
    return "Very Poor"


def find_spike_hop(latencies: List[Optional[float]], threshold_ms: float = 50.0) -> Optional[int]:
    """
    Return the index (0-based) of the hop where latency jumps by >= threshold_ms,
    or None if no such spike exists.
    """
    clean = [(i, v) for i, v in enumerate(latencies) if v is not None]
    for j in range(1, len(clean)):
        idx_a, lat_a = clean[j - 1]
        idx_b, lat_b = clean[j]
        if lat_b - lat_a >= threshold_ms:
            return idx_b
    return None
