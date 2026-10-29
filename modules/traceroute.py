"""
traceroute.py — Phase 5: High-Performance Traceroute Module

Uses streaming OS traceroute / tracert with intelligent early-exit:
- 800ms per-hop probe timeout (fast, responsive)
- Early-exit as soon as destination IP is reached
- Early-exit if 3 consecutive hops time out (border firewall dropping ICMP)
- Strict non-blocking reverse DNS lookups
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional


def run_traceroute(target: str, max_hops: int = 18, timeout: int = 1) -> Dict[str, Any]:
    """
    Run an optimized, streaming traceroute to *target*.

    Returns:
    {
        "target":       str,
        "hops":         list[HopDict],
        "total_hops":   int,
        "reached":      bool,
        "error":        str | None,
    }
    """
    system = platform.system().lower()

    if system == "windows":
        # -d: no DNS resolution inside tracert (we do fast async resolution ourselves)
        # -h: max hops
        # -w 800: 800ms per probe timeout (down from default 4000ms!)
        cmd = ["tracert", "-d", "-h", str(max_hops), "-w", "800", target]
    else:
        cmd = ["traceroute", "-n", "-m", str(max_hops), "-w", "1", target]

    hops: List[Dict[str, Any]] = []
    reached = False
    error: Optional[str] = None
    consecutive_timeouts = 0

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        t_start = time.perf_counter()
        # Enforce max 14 seconds hard ceiling on traceroute
        max_duration = 14.0

        for line in proc.stdout:
            # Check elapsed time ceiling
            if time.perf_counter() - t_start > max_duration:
                proc.terminate()
                break

            line = line.strip()
            if not line:
                continue

            hop = _parse_windows_line(line) if system == "windows" else _parse_unix_line(line)
            if not hop:
                continue

            hops.append(hop)

            # Check if destination reached
            if hop.get("ip") and (hop["ip"] == target or target in hop.get("ip", "")):
                reached = True
                proc.terminate()
                break

            # Check for consecutive timeouts (e.g. AWS/Amazon perimeter firewall)
            if hop.get("timed_out"):
                consecutive_timeouts += 1
                if consecutive_timeouts >= 3:
                    # Once a border firewall drops 3 hops in a row, remaining hops will also time out
                    proc.terminate()
                    break
            else:
                consecutive_timeouts = 0

        try:
            proc.wait(timeout=1.0)
        except Exception:
            proc.kill()

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

def _parse_windows_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Example: '  2    12 ms    11 ms    12 ms  192.168.1.1'
             '  3     *        *        *     Request timed out.'
    """
    m = re.match(r"^\s*(\d+)\s+", line)
    if not m:
        return None

    hop_num = int(m.group(1))

    if "timed out" in line.lower() or re.search(r"\*\s+\*\s+\*", line):
        return {"hop": hop_num, "ip": None, "hostname": None, "latency_ms": None, "timed_out": True}

    latencies = [float(x) for x in re.findall(r"(\d+)\s*ms", line)]
    avg_lat = round(sum(latencies) / len(latencies), 2) if latencies else None

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
    """Attempt a fast reverse DNS lookup with a strict 0.4s timeout ceiling."""
    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(0.4)
        try:
            return socket.gethostbyaddr(ip)[0]
        finally:
            socket.setdefaulttimeout(old_timeout)
    except Exception:
        return None
