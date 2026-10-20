"""
validator.py — Phase 2: Input Validation & Resolution
Validates user input (IPv4 / IPv6 / domain / localhost), resolves hostname to IP.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import time
from dataclasses import dataclass
from typing import Optional


# ── Domain regex pattern ───────────────────────────────────────────────────
_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}$"
)


@dataclass
class ValidationResult:
    """Structured result returned by the validator."""
    raw_input: str
    is_valid: bool
    input_type: str           # "ipv4" | "ipv6" | "domain" | "localhost" | "unknown"
    resolved_ip: Optional[str]
    hostname: Optional[str]
    error: Optional[str]
    resolution_time_ms: float


def validate(user_input: str, timeout: float = 5.0) -> ValidationResult:
    """
    Validate and resolve a user-supplied hostname or IP address.

    Returns a ValidationResult with full context for downstream modules.
    """
    raw = user_input.strip()
    if not raw:
        return ValidationResult(
            raw_input="",
            is_valid=False,
            input_type="unknown",
            resolved_ip=None,
            hostname=None,
            error="Input is empty. Please enter a valid domain or IP address.",
            resolution_time_ms=0.0,
        )

    # ── Step 1: Detect IP or Domain Type ─────────────────────────────────────
    input_type = "unknown"
    try:
        parsed_ip = ipaddress.ip_address(raw)
        input_type = "ipv6" if isinstance(parsed_ip, ipaddress.IPv6Address) else "ipv4"
    except ValueError:
        if raw.lower() == "localhost":
            input_type = "localhost"
        elif _DOMAIN_RE.match(raw):
            input_type = "domain"
        else:
            return ValidationResult(
                raw_input=raw,
                is_valid=False,
                input_type="unknown",
                resolved_ip=None,
                hostname=None,
                error=f"'{raw}' is not a valid IP address or hostname.",
                resolution_time_ms=0.0,
            )

    # ── Step 2: Resolve Host / IP ──────────────────────────────────────────
    socket.setdefaulttimeout(timeout)
    t0 = time.perf_counter()
    try:
        if input_type in ("ipv4", "ipv6"):
            resolved_ip = raw
            try:
                hostname = socket.gethostbyaddr(raw)[0]
            except Exception:
                hostname = raw

        elif input_type == "localhost":
            resolved_ip = "127.0.0.1"
            hostname = "localhost"

        else:  # domain
            resolved_ip = socket.gethostbyname(raw)
            hostname = raw

        elapsed = (time.perf_counter() - t0) * 1000
        return ValidationResult(
            raw_input=raw,
            is_valid=True,
            input_type=input_type,
            resolved_ip=resolved_ip,
            hostname=hostname,
            error=None,
            resolution_time_ms=round(elapsed, 2),
        )

    except socket.timeout:
        elapsed = (time.perf_counter() - t0) * 1000
        return ValidationResult(
            raw_input=raw,
            is_valid=False,
            input_type=input_type,
            resolved_ip=None,
            hostname=None,
            error=f"DNS resolution timed out after {timeout}s.",
            resolution_time_ms=round(elapsed, 2),
        )
    except socket.gaierror as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return ValidationResult(
            raw_input=raw,
            is_valid=False,
            input_type=input_type,
            resolved_ip=None,
            hostname=None,
            error=f"DNS resolution failed: {exc}",
            resolution_time_ms=round(elapsed, 2),
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return ValidationResult(
            raw_input=raw,
            is_valid=False,
            input_type=input_type,
            resolved_ip=None,
            hostname=None,
            error=f"Validation failed: {exc}",
            resolution_time_ms=round(elapsed, 2),
        )
