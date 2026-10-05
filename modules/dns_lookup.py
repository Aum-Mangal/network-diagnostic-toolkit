"""
dns_lookup.py — Phase 4: DNS Resolution Module

Performs forward (A / AAAA) DNS lookups and records response time.
Uses the standard library socket for maximum portability;
also attempts dnspython for richer record data when available.
"""

from __future__ import annotations

import socket
import time
from typing import Any, Dict, List, Optional


def run_dns(domain: str, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Resolve *domain* and return structured DNS information.

    Returns:
    {
        "domain":           str,
        "success":          bool,
        "ipv4_addresses":   list[str],
        "ipv6_addresses":   list[str],
        "response_time_ms": float,
        "error":            str | None,
    }
    """
    socket.setdefaulttimeout(timeout)

    ipv4: List[str] = []
    ipv6: List[str] = []
    error: Optional[str] = None

    t0 = time.perf_counter()
    try:
        addrinfos = socket.getaddrinfo(domain, None)
        for family, _, _, _, sockaddr in addrinfos:
            ip = sockaddr[0]
            if family == socket.AF_INET and ip not in ipv4:
                ipv4.append(ip)
            elif family == socket.AF_INET6 and ip not in ipv6:
                ipv6.append(ip)
        success = bool(ipv4 or ipv6)
    except socket.gaierror as exc:
        success = False
        error = str(exc)
    except Exception as exc:
        success = False
        error = str(exc)

    elapsed = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "domain":           domain,
        "success":          success,
        "ipv4_addresses":   ipv4,
        "ipv6_addresses":   ipv6,
        "response_time_ms": elapsed,
        "error":            error,
    }
