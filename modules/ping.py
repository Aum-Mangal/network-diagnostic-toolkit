"""
ping.py — Phase 3: ICMP Ping & TCP Fallback Ping Module

Uses the OS ping command (ICMP) and automatically falls back to
TCP SYN Handshake measurement (ports 443/80) when enterprise firewalls
block ICMP Echo Requests (e.g. amazon.com, microsoft.com, cloudflare).
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
import time
from typing import Dict, Any, List, Optional


def tcp_syn_ping(target: str, ports: tuple[int, ...] = (443, 80), timeout: float = 2.0) -> Optional[tuple[int, float]]:
    """
    Measure round-trip time of a TCP 3-way handshake (SYN -> SYN-ACK).
    Useful when target blocks ICMP Echo Requests at border firewalls.
    """
    for port in ports:
        t0 = time.perf_counter()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((target, port))
            rtt = (time.perf_counter() - t0) * 1000
            s.close()
            return port, round(rtt, 2)
        except Exception:
            continue
    return None


def run_ping(target: str, count: int = 4, timeout: int = 1) -> Dict[str, Any]:
    """
    Ping *target* with *count* ICMP echo requests.
    If 100% packet loss is observed, automatically executes a TCP SYN handshake
    to determine if the host is alive behind an ICMP-filtering firewall.

    Returns structured data:
    {
        "target": str,
        "sent":         int,
        "received":     int,
        "lost":         int,
        "packet_loss":  float,
        "min_latency":  float,
        "avg_latency":  float,
        "max_latency":  float,
        "jitter_ms":    float,
        "status":       str,     # "HEALTHY" | "DEGRADED" | "UNREACHABLE" | "ICMP_BLOCKED_TCP_OK"
        "raw_times":    list[float],
        "icmp_blocked": bool,
        "tcp_fallback": dict | None,
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
        pass

    lost = sent - received
    packet_loss = (lost / sent * 100) if sent else 100.0

    min_lat = round(min(raw_times), 2) if raw_times else 0.0
    max_lat = round(max(raw_times), 2) if raw_times else 0.0
    avg_lat = round(sum(raw_times) / len(raw_times), 2) if raw_times else 0.0

    # Calculate Jitter (RFC 3393 packet delay variation)
    jitter = 0.0
    if len(raw_times) > 1:
        jitter = round(
            sum(abs(raw_times[i] - raw_times[i - 1]) for i in range(1, len(raw_times))) / (len(raw_times) - 1),
            2
        )

    icmp_blocked = False
    tcp_fallback_data = None

    # If ICMP completely failed, check TCP SYN Handshake
    if received == 0:
        tcp_res = tcp_syn_ping(target)
        if tcp_res:
            port, tcp_rtt = tcp_res
            icmp_blocked = True
            tcp_fallback_data = {"port": port, "rtt_ms": tcp_rtt}
            status = "ICMP_BLOCKED_TCP_OK"
            avg_lat = tcp_rtt
            min_lat = tcp_rtt
            max_lat = tcp_rtt
            raw_times = [tcp_rtt]
        else:
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
        "jitter_ms":    jitter,
        "status":       status,
        "raw_times":    raw_times,
        "icmp_blocked": icmp_blocked,
        "tcp_fallback": tcp_fallback_data,
    }


# ── Parsers ─────────────────────────────────────────────────────────────────

def _parse_times(output: str, system: str) -> list[float]:
    """Extract individual round-trip times from ping output."""
    times: list[float] = []
    if system == "windows":
        for m in re.finditer(r"[Tt]ime[=<](\d+(?:\.\d+)?)ms", output):
            times.append(float(m.group(1)))
    else:
        for m in re.finditer(r"time=(\d+(?:\.\d+)?)\s*ms", output):
            times.append(float(m.group(1)))
    return times


def _parse_counts(output: str, system: str, count: int) -> tuple[int, int]:
    """Parse sent and received counts from ping output."""
    sent = count
    received = 0

    if system == "windows":
        m_sent = re.search(r"Sent\s*=\s*(\d+)", output)
        m_recv = re.search(r"Received\s*=\s*(\d+)", output)
        if m_sent:
            sent = int(m_sent.group(1))
        if m_recv:
            received = int(m_recv.group(1))
    else:
        m = re.search(r"(\d+)\s+packets transmitted,\s+(\d+)\s+(?:packets\s+)?received", output)
        if m:
            sent = int(m.group(1))
            received = int(m.group(2))

    return sent, received
