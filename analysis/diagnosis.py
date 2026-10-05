"""
diagnosis.py — Natural Language Intent Detector (Phase 12 & 13).

Parses a natural-language query to extract:
  - The target host/IP
  - The diagnostic intent (used to select modules)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


INTENT_KEYWORDS = {
    "slow":         ["slow", "sluggish", "lag", "lagging", "delay", "delayed", "latency"],
    "connectivity": ["connect", "connection", "reach", "reachable", "ping", "online", "alive"],
    "https":        ["https", "ssl", "tls", "secure", "certificate"],
    "http":         ["http", "website", "web", "page", "browse"],
    "ssh":          ["ssh", "remote", "shell"],
    "dns":          ["dns", "resolve", "resolution", "domain"],
    "route":        ["route", "path", "traceroute", "hops", "routing"],
    "access":       ["access", "open", "available", "down", "unreachable", "blocked"],
    "full":         ["diagnose", "diagnostic", "check", "scan", "analyse", "analyze", "everything"],
}

# Rough pattern to extract a domain or IP from a sentence
_HOST_RE = re.compile(
    r"\b(?:"
    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}"   # domain
    r"|"
    r"(?:\d{1,3}\.){3}\d{1,3}"                                                 # IPv4
    r")\b"
)


@dataclass
class ParsedQuery:
    raw_query: str
    target: Optional[str]
    intent: str
    natural_language: bool   # True if user typed a sentence, False if just a hostname


def parse_query(query: str) -> ParsedQuery:
    """
    Determine whether the query is natural language or a bare host/IP,
    extract the target, and map to an intent string.
    """
    q = query.strip()

    # Detect if this is a bare hostname / IP (single token, no spaces)
    tokens = q.split()
    if len(tokens) == 1:
        return ParsedQuery(
            raw_query=q,
            target=q,
            intent="full",
            natural_language=False,
        )

    # Natural language: find host
    host_match = _HOST_RE.search(q)
    target = host_match.group(0) if host_match else None

    # Determine intent by keyword matching (first match wins by priority order)
    q_lower = q.lower()
    intent = "full"
    for intent_name, keywords in INTENT_KEYWORDS.items():
        if any(kw in q_lower for kw in keywords):
            intent = intent_name
            break

    return ParsedQuery(
        raw_query=q,
        target=target,
        intent=intent,
        natural_language=True,
    )
