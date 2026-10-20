"""
diagnosis.py — Natural Language Intent & Target Detector (Phase 12 & 13).

Parses a natural-language query to extract:
  - The target host/IP (supports IPv4, IPv6, domain names, localhost)
  - Custom port numbers if mentioned (e.g. "port 8080")
  - The diagnostic intent (used to select modules)
  - Clarification metadata if no valid target was found
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from typing import List, Optional


INTENT_KEYWORDS = {
    "slow": [
        "slow", "sluggish", "lag", "lagging", "delay", "delayed", "latency",
        "bufferbloat", "high ping", "taking long", "taking forever", "timeout"
    ],
    "connectivity": [
        "connect", "connection", "reach", "reachable", "ping", "online",
        "alive", "up", "drop", "dropping", "disconnect", "packet loss"
    ],
    "https": [
        "https", "ssl", "tls", "secure", "certificate", "cert", "port 443"
    ],
    "http": [
        "http", "website", "web", "page", "browse", "port 80"
    ],
    "ssh": [
        "ssh", "remote", "shell", "port 22"
    ],
    "dns": [
        "dns", "resolve", "resolution", "domain", "nameserver", "lookup", "mx", "ns"
    ],
    "route": [
        "route", "path", "traceroute", "hops", "routing", "trace", "bottleneck"
    ],
    "access": [
        "access", "open", "available", "down", "unreachable", "blocked",
        "firewall", "port", "ports", "service"
    ],
    "full": [
        "diagnose", "diagnostic", "check", "scan", "analyse", "analyze",
        "everything", "full", "all", "report"
    ],
}

# Domain regex (supports multi-level domains like cloud.google.com, bbc.co.uk)
_DOMAIN_RE = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"
)

# Regex to detect port specifications (e.g. "port 8080", "ports 80, 443", ":8443")
_PORT_RE = re.compile(r"(?:\bports?\s+|\bon ports?\s+)([0-9,\s]+)|(?<!:):([0-9]{1,5})\b", re.IGNORECASE)


@dataclass
class ParsedQuery:
    raw_query: str
    target: Optional[str]
    intent: str
    natural_language: bool
    custom_ports: Optional[List[int]] = None
    needs_target: bool = False
    clarification_prompt: str = ""
    extracted_target_type: str = "unknown"  # "domain" | "ipv4" | "ipv6" | "localhost" | "none"


def _clean_token(token: str) -> str:
    """Strip common sentence punctuation from the edges of a potential target token."""
    return token.strip(" \t\r\n.,;:?!'\"()[]{}<>")


def _is_valid_ip(token: str) -> Optional[str]:
    """Return 'ipv4' or 'ipv6' if token is a valid IP, else None."""
    cleaned = _clean_token(token)
    try:
        ip = ipaddress.ip_address(cleaned)
        return "ipv6" if isinstance(ip, ipaddress.IPv6Address) else "ipv4"
    except ValueError:
        return None


def parse_query(query: str) -> ParsedQuery:
    """
    Determine whether the query is natural language or a bare host/IP,
    extract the target, optional ports, and map to an intent string.
    """
    q = query.strip()
    if not q:
        return ParsedQuery(
            raw_query="",
            target=None,
            intent="full",
            natural_language=False,
            needs_target=True,
            clarification_prompt="Query is empty. Please enter a destination domain or IP address.",
            extracted_target_type="none",
        )

    # ── Single token check (bare host or IP) ───────────────────────────────────
    tokens = q.split()
    if len(tokens) == 1:
        single = _clean_token(tokens[0])
        ip_type = _is_valid_ip(single)
        if ip_type:
            target_type = ip_type
        elif single.lower() == "localhost":
            target_type = "localhost"
        elif _DOMAIN_RE.fullmatch(single):
            target_type = "domain"
        else:
            target_type = "unknown"

        return ParsedQuery(
            raw_query=q,
            target=single,
            intent="full",
            natural_language=False,
            needs_target=False,
            extracted_target_type=target_type,
        )

    # ── Natural Language Query: Extract Target ────────────────────────────────
    target: Optional[str] = None
    target_type = "none"

    # 1. First look for IPv4 or IPv6 tokens
    for tok in tokens:
        cleaned = _clean_token(tok)
        ip_type = _is_valid_ip(cleaned)
        if ip_type:
            target = cleaned
            target_type = ip_type
            break

    # 2. Look for domains if no IP found
    if not target:
        domain_match = _DOMAIN_RE.search(q)
        if domain_match:
            target = _clean_token(domain_match.group(0))
            target_type = "domain"

    # 3. Check for localhost
    if not target and re.search(r"\blocalhost\b", q, re.IGNORECASE):
        target = "localhost"
        target_type = "localhost"

    # ── Extract Custom Ports if mentioned ─────────────────────────────────────
    custom_ports: Optional[List[int]] = None
    query_without_target = q.replace(target, "") if target else q
    port_match = _PORT_RE.search(query_without_target)
    if port_match:
        port_str = port_match.group(1) or port_match.group(2)
        if port_str:
            extracted = []
            for piece in re.split(r"[, ]+", port_str.strip()):
                if piece.isdigit():
                    p_val = int(piece)
                    if 1 <= p_val <= 65535:
                        extracted.append(p_val)
            if extracted:
                custom_ports = extracted

    # ── Determine Intent ──────────────────────────────────────────────────────
    q_lower = q.lower()
    intent = "full"
    
    # Priority matching
    if custom_ports:
        intent = "access"
    else:
        for intent_name, keywords in INTENT_KEYWORDS.items():
            if any(kw in q_lower for kw in keywords):
                intent = intent_name
                break

    # ── Handle Missing Target ─────────────────────────────────────────────────
    needs_target = target is None
    clarification = ""
    if needs_target:
        clarification = (
            f"No destination target (domain or IP) was found in your query: \"{q}\".\n"
            "Please provide a destination host (e.g. google.com or 1.1.1.1)."
        )

    return ParsedQuery(
        raw_query=q,
        target=target,
        intent=intent,
        natural_language=True,
        custom_ports=custom_ports,
        needs_target=needs_target,
        clarification_prompt=clarification,
        extracted_target_type=target_type,
    )
