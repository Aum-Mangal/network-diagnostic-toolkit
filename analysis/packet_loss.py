"""
packet_loss.py — Packet-loss analysis helpers.
"""
from __future__ import annotations


def classify_packet_loss(pct: float) -> str:
    if pct == 0:
        return "None"
    elif pct < 5:
        return "Negligible"
    elif pct < 10:
        return "Moderate"
    elif pct < 30:
        return "High"
    return "Critical"


def loss_severity(pct: float) -> str:
    if pct == 0:
        return "info"
    elif pct < 10:
        return "warning"
    return "critical"
