"""
port_scanner.py — Phase 6: Port Scanner Module

Uses Python sockets (TCP connect scan) to check port reachability.
Maps common ports to their well-known service names.
"""

from __future__ import annotations

import socket
import concurrent.futures
from typing import Any, Dict, List


# ── Common port → service name map ──────────────────────────────────────────
SERVICE_MAP: Dict[int, str] = {
    21:   "FTP",
    22:   "SSH",
    23:   "Telnet",
    25:   "SMTP",
    53:   "DNS",
    80:   "HTTP",
    110:  "POP3",
    143:  "IMAP",
    443:  "HTTPS",
    445:  "SMB",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    6379: "Redis",
    8080: "HTTP-ALT",
    8443: "HTTPS-ALT",
    27017: "MongoDB",
}

DEFAULT_PORTS = [22, 53, 80, 443, 8080]


def run_port_scan(
    target: str,
    ports: List[int] = None,
    timeout: float = 1.0,
    max_workers: int = 20,
) -> Dict[str, Any]:
    """
    TCP connect-scan *target* on the given *ports*.

    Returns:
    {
        "target": str,
        "ports": {
            "80": {"service": "HTTP", "status": "OPEN"},
            "443": {"service": "HTTPS", "status": "CLOSED"},
            ...
        },
        "open_count":   int,
        "closed_count": int,
    }
    """
    if ports is None:
        ports = DEFAULT_PORTS

    port_results: Dict[str, Dict[str, str]] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_check_port, target, port, timeout): port
            for port in ports
        }
        for future in concurrent.futures.as_completed(futures):
            port = futures[future]
            status = future.result()
            port_results[str(port)] = {
                "service": SERVICE_MAP.get(port, "UNKNOWN"),
                "status":  status,
            }

    open_count   = sum(1 for v in port_results.values() if v["status"] == "OPEN")
    closed_count = len(port_results) - open_count

    return {
        "target":       target,
        "ports":        port_results,
        "open_count":   open_count,
        "closed_count": closed_count,
    }


def _check_port(target: str, port: int, timeout: float) -> str:
    """Return 'OPEN' if a TCP connection succeeds, else 'CLOSED'."""
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return "OPEN"
    except (socket.timeout, ConnectionRefusedError, OSError):
        return "CLOSED"
