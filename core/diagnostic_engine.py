"""
diagnostic_engine.py — Phase 1 / 13: Orchestrates all diagnostic modules.

The engine selects which modules to run based on intent (smart planner)
and collects results into a unified payload for the result processor.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.validator import ValidationResult


# ── Intent → Module mapping (Phase 13) ─────────────────────────────────────
INTENT_MODULE_MAP: Dict[str, List[str]] = {
    "connectivity": ["dns", "ping"],
    "performance":  ["ping", "traceroute"],
    "slow":         ["ping", "traceroute"],
    "access":       ["dns", "ping", "traceroute", "port"],
    "https":        ["dns", "port_443"],
    "http":         ["dns", "port_80"],
    "ssh":          ["dns", "port_22"],
    "full":         ["dns", "ping", "traceroute", "port", "network_info"],
    "route":        ["traceroute"],
    "dns":          ["dns"],
}


@dataclass
class DiagnosticPayload:
    """Aggregated results from all executed modules."""
    target: str
    resolved_ip: Optional[str]
    intent: str
    modules_run: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    total_time_ms: float = 0.0


class DiagnosticEngine:
    """
    Orchestrates diagnostic modules based on intent.
    Each module is imported lazily to keep startup fast.
    """

    def __init__(self, validation: ValidationResult):
        self.validation = validation
        self.target = validation.resolved_ip or validation.raw_input
        self.display_target = validation.raw_input

    # ── Public API ──────────────────────────────────────────────────────────

    def run(
        self,
        intent: str = "full",
        custom_ports: Optional[List[int]] = None,
        ping_count: int = 4,
    ) -> DiagnosticPayload:
        """
        Run the diagnostic suite chosen by *intent*.
        Returns a DiagnosticPayload with all results.
        """
        modules = INTENT_MODULE_MAP.get(intent, INTENT_MODULE_MAP["full"])
        payload = DiagnosticPayload(
            target=self.display_target,
            resolved_ip=self.target,
            intent=intent,
        )

        t_start = time.perf_counter()

        for mod_name in modules:
            self._run_module(mod_name, payload, ping_count, custom_ports)

        # Always add local network info for "full" scan
        if intent == "full" and "network_info" not in payload.modules_run:
            self._run_module("network_info", payload, ping_count, custom_ports)

        payload.total_time_ms = round((time.perf_counter() - t_start) * 1000, 2)
        return payload

    # ── Internal dispatch ───────────────────────────────────────────────────

    def _run_module(
        self,
        name: str,
        payload: DiagnosticPayload,
        ping_count: int,
        custom_ports: Optional[List[int]],
    ) -> None:
        """Dispatch a single module by name and store its result."""
        try:
            if name == "ping":
                from modules.ping import run_ping
                payload.results["ping"] = run_ping(self.target, count=ping_count)
                payload.modules_run.append("ping")

            elif name == "dns":
                from modules.dns_lookup import run_dns
                payload.results["dns"] = run_dns(self.display_target)
                payload.modules_run.append("dns")

            elif name == "traceroute":
                from modules.traceroute import run_traceroute
                payload.results["traceroute"] = run_traceroute(self.target)
                payload.modules_run.append("traceroute")

            elif name in ("port", "port_80", "port_443", "port_22"):
                from modules.port_scanner import run_port_scan
                ports = custom_ports or [22, 53, 80, 443, 8080]
                if name == "port_443":
                    ports = [443]
                elif name == "port_80":
                    ports = [80]
                elif name == "port_22":
                    ports = [22]
                payload.results["port"] = run_port_scan(self.target, ports)
                if "port" not in payload.modules_run:
                    payload.modules_run.append("port")

            elif name == "network_info":
                from modules.network_info import run_network_info
                payload.results["network_info"] = run_network_info()
                payload.modules_run.append("network_info")

        except Exception as exc:
            payload.errors[name] = str(exc)
