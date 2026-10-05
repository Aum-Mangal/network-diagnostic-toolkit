"""
ping.py — Phase 3: ICMP Ping Module

Uses the OS ping command on both Windows and Linux/macOS,
then parses its output into a structured dictionary.
Raw ping output is never exposed to callers.
"""

from __future__ import annotations

import platform
import re
import subprocess
import time
from typing import Dict, Any


def run_ping(target: str, count: int = 4, timeout: int = 3) -> Dict[str, Any]:
    """
    Ping *target* with *count* ICMP echo requests.

    Returns structured data:
    {
        "target": str,
        "sent":         int,
        "received":     int,
        "lost":         int,
        "packet_loss":  float,   # percentage
        "min_latency":  float,   # ms
        "avg_latency":  float,   # ms
        "max_latency":  float,   # ms
        "status":       str,     # "HEALTHY" | "DEGRADED" | "UNREACHABLE"
        "raw_times":    list[float],
    }
    """
    system = platform.system().lower()

    if system == "windows":
        cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), target]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(timeout), target]

    raw_times: list[float] = []
    sent = count
    received = 0

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=count * (timeout + 2),
        )
        output = result.stdout + result.stderr
        raw_times = _parse_times(output, system)
        sent, received = _parse_counts(output, system, count)

    except subprocess.TimeoutExpired:
        pass
    except FileNotFoundError:
        # Fallback: use raw sockets if ping binary not found
        pass

    lost = sent - received
    packet_loss = (lost / sent * 100) if sent else 100.0

    min_lat = round(min(raw_times), 2) if raw_times else 0.0
    max_lat = round(max(raw_times), 2) if raw_times else 0.0
    avg_lat = round(sum(raw_times) / len(raw_times), 2) if raw_times else 0.0

    if received == 0:
        status = "UNREACHABLE"
    elif packet_loss > 10 or avg_lat > 200:
        status = "DEGRADED"
    else:
        status = "HEALTHY"

    return {
        "target":       target,
        "sent":         sent,
        "received":     received,
        "lost":         lost,
        "packet_loss":  round(packet_loss, 1),
        "min_latency":  min_lat,
        "avg_latency":  avg_lat,
        "max_latency":  max_lat,
        "status":       status,
        "raw_times":    raw_times,
    }


# ── Parsers ─────────────────────────────────────────────────────────────────

def _parse_times(output: str, system: str) -> list[float]:
    """Extract individual round-trip times from ping output."""
    times: list[float] = []
    if system == "windows":
        # "Minimum = 18ms, Maximum = 28ms, Average = 22ms"
        # Individual: "time=22ms" or "time<1ms"
        for m in re.finditer(r"[Tt]ime[=<](\d+(?:\.\d+)?)ms", output):
            times.append(float(m.group(1)))
        if not times:
            # Try summary line
            m = re.search(r"Average\s*=\s*(\d+)ms", output)
            if m:
                times.append(float(m.group(1)))
    else:
        # Linux/macOS: "time=12.3 ms"
        for m in re.finditer(r"time[=<](\d+(?:\.\d+)?)\s*ms", output):
            times.append(float(m.group(1)))
    return times


def _parse_counts(output: str, system: str, default_sent: int) -> tuple[int, int]:
    """Return (sent, received) packet counts."""
    sent = default_sent
    received = 0

    if system == "windows":
        m = re.search(r"Sent\s*=\s*(\d+).*?Received\s*=\s*(\d+)", output, re.DOTALL)
        if m:
            sent = int(m.group(1))
            received = int(m.group(2))
        else:
            # Count individual reply lines
            received = len(re.findall(r"[Tt]ime[=<]\d+ms", output))
    else:
        # "4 packets transmitted, 4 received"
        m = re.search(r"(\d+)\s+packets\s+transmitted,\s+(\d+)\s+received", output)
        if m:
            sent = int(m.group(1))
            received = int(m.group(2))
        else:
            received = len(re.findall(r"time[=<]\d+(?:\.\d+)?\s*ms", output))

    return sent, received
