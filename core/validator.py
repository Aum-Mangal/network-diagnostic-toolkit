"""
validator.py — Phase 2: Input Validation & Resolution
Validates user input (IP / domain), resolves hostname to IP.
"""

import re
import socket
import time
from dataclasses import dataclass
from typing import Optional


# ── Regex patterns ─────────────────────────────────────────────────────────
_IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)
_IPV6_RE = re.compile(
    r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
    r"|^::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}$"
    r"|^(?:[0-9a-fA-F]{1,4}:){1,7}:$"
    r"|^::$"
    r"|^(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}$"
    r"|^(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}$"
    r"|^(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}$"
    r"|^(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}$"
    r"|^(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}$"
    r"|^[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}$"
)
_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}$"
)


@dataclass
class ValidationResult:
    """Structured result returned by the validator."""
    raw_input: str
    is_valid: bool
    input_type: str           # "ipv4" | "ipv6" | "domain" | "unknown"
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

    # ── Step 1: detect type ────────────────────────────────────────────────
    if _IPV4_RE.match(raw):
        input_type = "ipv4"
    elif _IPV6_RE.match(raw):
        input_type = "ipv6"
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

    # ── Step 2: resolve ────────────────────────────────────────────────────
    socket.setdefaulttimeout(timeout)
    t0 = time.perf_counter()
    try:
        if input_type in ("ipv4", "ipv6"):
            # Already an IP — do a reverse lookup for hostname (best-effort)
            resolved_ip = raw
            try:
                hostname = socket.gethostbyaddr(raw)[0]
            except Exception:
                hostname = raw
        else:
            # Domain — forward DNS
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
