"""
traceroute.py — Phase 5: Traceroute Module

Uses the OS traceroute / tracert command and parses each hop into
structured data for visualization and analysis.
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
from typing import Any, Dict, List, Optional


def run_traceroute(target: str, max_hops: int = 30, timeout: int = 3) -> Dict[str, Any]:
    """
    Run a traceroute to *target* and parse the results.

    Returns:
    {
        "target":       str,
        "hops":         list[HopDict],
        "total_hops":   int,
        "reached":      bool,
        "error":        str | None,
    }

    HopDict = {
        "hop":        int,
        "ip":         str | None,
        "hostname":   str | None,
        "latency_ms": float | None,
        "timed_out":  bool,
    }
    """
    system = platform.system().lower()

    if system == "windows":
        cmd = ["tracert", "-d", "-h", str(max_hops), "-w", str(timeout * 1000), target]
    else:
        cmd = ["traceroute", "-n", "-m", str(max_hops), "-w", str(timeout), target]

    hops: List[Dict[str, Any]] = []
    reached = False
    error: Optional[str] = None

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max_hops * (timeout + 2),
        )
        output = proc.stdout + proc.stderr
        hops, reached = _parse_output(output, system, target)
    except subprocess.TimeoutExpired:
        error = "Traceroute timed out"
    except FileNotFoundError:
        error = "traceroute/tracert binary not found"
    except Exception as exc:
        error = str(exc)

    return {
        "target":     target,
        "hops":       hops,
        "total_hops": len(hops),
        "reached":    reached,
        "error":      error,
    }


# ── Parsers ─────────────────────────────────────────────────────────────────

def _parse_output(
    output: str, system: str, target: str
) -> tuple[List[Dict[str, Any]], bool]:
    hops: List[Dict[str, Any]] = []
    reached = False

    lines = output.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if system == "windows":
            hop = _parse_windows_line(line)
        else:
            hop = _parse_unix_line(line)

        if hop:
            hops.append(hop)
            if hop.get("ip") and hop["ip"] == target:
                reached = True

    return hops, reached


def _parse_windows_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Example: '  2    12 ms    11 ms    12 ms  192.168.1.1'
             '  3     *        *        *     Request timed out.'
    """
    # Match hop number at start
    m = re.match(r"^\s*(\d+)\s+", line)
    if not m:
        return None

    hop_num = int(m.group(1))

    if "timed out" in line.lower() or re.search(r"\*\s+\*\s+\*", line):
        return {"hop": hop_num, "ip": None, "hostname": None, "latency_ms": None, "timed_out": True}

    # Extract all latency values (ms)
    latencies = [float(x) for x in re.findall(r"(\d+)\s*ms", line)]
    avg_lat = round(sum(latencies) / len(latencies), 2) if latencies else None

    # Extract IP at end
    ip_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})\s*$", line)
    ip = ip_match.group(1) if ip_match else None
    hostname = _reverse_lookup(ip) if ip else None

    return {
        "hop":        hop_num,
        "ip":         ip,
        "hostname":   hostname,
        "latency_ms": avg_lat,
        "timed_out":  False,
    }


def _parse_unix_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Example: ' 1  192.168.1.1  1.234 ms  1.456 ms  1.789 ms'
             ' 3  * * *'
    """
    m = re.match(r"^\s*(\d+)\s+", line)
    if not m:
        return None

    hop_num = int(m.group(1))

    if re.search(r"\*\s+\*\s+\*", line):
        return {"hop": hop_num, "ip": None, "hostname": None, "latency_ms": None, "timed_out": True}

    ip_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", line)
    ip = ip_match.group(1) if ip_match else None

    latencies = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*ms", line)]
    avg_lat = round(sum(latencies) / len(latencies), 2) if latencies else None

    hostname = _reverse_lookup(ip) if ip else None

    return {
        "hop":        hop_num,
        "ip":         ip,
        "hostname":   hostname,
        "latency_ms": avg_lat,
        "timed_out":  False,
    }


def _reverse_lookup(ip: str) -> Optional[str]:
    """Attempt a reverse DNS lookup; silently return None on failure."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None
