"""
result_processor.py — Phase 8 & 9: Analysis, Scoring & Diagnostic Rules Engine

Takes the raw DiagnosticPayload and produces human-readable analysis,
a numeric health score, detected problems, possible causes, and recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.diagnostic_engine import DiagnosticPayload


# ── Scoring weights ─────────────────────────────────────────────────────────
#  Each component contributes up to its weight toward 100.
WEIGHTS = {
    "ping":       40,
    "dns":        20,
    "traceroute": 20,
    "port":       10,
    "network":    10,
}

# ── Latency thresholds (ms) ─────────────────────────────────────────────────
LATENCY_EXCELLENT = 50
LATENCY_GOOD      = 100
LATENCY_WARN      = 200

# ── Packet loss thresholds (%) ──────────────────────────────────────────────
LOSS_WARN     = 5
LOSS_HIGH     = 10
LOSS_CRITICAL = 30

# ── Hop-latency spike threshold ─────────────────────────────────────────────
HOP_SPIKE_MS = 50   # delta that counts as a routing bottleneck


@dataclass
class Problem:
    severity: str          # "info" | "warning" | "critical"
    module: str
    description: str
    detail: str = ""


@dataclass
class ProcessedResult:
    payload: DiagnosticPayload
    health_score: int                   # 0–100
    overall_status: str                 # "HEALTHY" | "WARNING" | "CRITICAL" | "UNKNOWN"
    problems: List[Problem] = field(default_factory=list)
    possible_causes: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    module_scores: Dict[str, int] = field(default_factory=dict)

    @property
    def status_emoji(self) -> str:
        return {"HEALTHY": "🟢", "WARNING": "🟡", "CRITICAL": "🔴", "UNKNOWN": "⚪"}.get(
            self.overall_status, "⚪"
        )


class ResultProcessor:
    """Applies the diagnostic rules engine to a DiagnosticPayload."""

    def process(self, payload: DiagnosticPayload) -> ProcessedResult:
        result = ProcessedResult(payload=payload, health_score=0, overall_status="UNKNOWN")

        self._analyze_ping(payload, result)
        self._analyze_dns(payload, result)
        self._analyze_traceroute(payload, result)
        self._analyze_ports(payload, result)

        result.health_score = self._compute_score(result)
        result.overall_status = self._status_from_score(result.health_score)
        self._build_causes_and_recs(result)

        return result

    # ── Module analysers ────────────────────────────────────────────────────

    def _analyze_ping(self, payload: DiagnosticPayload, result: ProcessedResult) -> None:
        ping = payload.results.get("ping")
        if not ping:
            return

        score = WEIGHTS["ping"]  # start full, deduct

        loss = ping.get("packet_loss", 0)
        avg  = ping.get("avg_latency", 0)
        recv = ping.get("received", 0)

        if recv == 0:
            result.problems.append(Problem(
                severity="critical", module="ping",
                description="Target is unreachable (0 packets received)",
                detail=f"Sent {ping.get('sent', 4)} packets, received 0"
            ))
            score = 0
        else:
            # Packet loss
            if loss >= LOSS_CRITICAL:
                result.problems.append(Problem(
                    severity="critical", module="ping",
                    description=f"Critical packet loss: {loss:.1f}%",
                    detail="Severe connectivity degradation"
                ))
                score -= 30
            elif loss >= LOSS_HIGH:
                result.problems.append(Problem(
                    severity="warning", module="ping",
                    description=f"High packet loss: {loss:.1f}%",
                    detail="Network instability detected"
                ))
                score -= 20
            elif loss >= LOSS_WARN:
                result.problems.append(Problem(
                    severity="info", module="ping",
                    description=f"Minor packet loss: {loss:.1f}%",
                    detail="Occasional drops"
                ))
                score -= 8

            # Latency
            if avg > LATENCY_WARN:
                result.problems.append(Problem(
                    severity="warning", module="ping",
                    description=f"High average latency: {avg:.1f} ms",
                    detail=f"Expected < {LATENCY_GOOD} ms for normal operation"
                ))
                score -= 15
            elif avg > LATENCY_GOOD:
                result.problems.append(Problem(
                    severity="info", module="ping",
                    description=f"Elevated latency: {avg:.1f} ms",
                    detail="Slightly above optimal"
                ))
                score -= 7

        result.module_scores["ping"] = max(0, score)

    def _analyze_dns(self, payload: DiagnosticPayload, result: ProcessedResult) -> None:
        dns = payload.results.get("dns")
        if not dns:
            return

        score = WEIGHTS["dns"]

        if not dns.get("success"):
            result.problems.append(Problem(
                severity="critical", module="dns",
                description="DNS resolution failed",
                detail=dns.get("error", "Unknown DNS error")
            ))
            score = 0
        else:
            resp_ms = dns.get("response_time_ms", 0)
            if resp_ms > 500:
                result.problems.append(Problem(
                    severity="warning", module="dns",
                    description=f"Slow DNS response: {resp_ms:.0f} ms",
                    detail="DNS server may be overloaded"
                ))
                score -= 8

        result.module_scores["dns"] = max(0, score)

    def _analyze_traceroute(self, payload: DiagnosticPayload, result: ProcessedResult) -> None:
        tr = payload.results.get("traceroute")
        if not tr:
            return

        score = WEIGHTS["traceroute"]
        hops = tr.get("hops", [])

        if not hops:
            result.problems.append(Problem(
                severity="warning", module="traceroute",
                description="Traceroute produced no hops",
                detail="May indicate firewall blocking ICMP"
            ))
            score -= 10
        else:
            # Detect latency spikes between consecutive hops
            latencies = [
                h["latency_ms"] for h in hops if h.get("latency_ms") is not None
            ]
            for i in range(1, len(latencies)):
                delta = latencies[i] - latencies[i - 1]
                if delta > HOP_SPIKE_MS:
                    hop_num = hops[i].get("hop", i + 1)
                    result.problems.append(Problem(
                        severity="warning", module="traceroute",
                        description=f"Latency spike at hop {hop_num}: +{delta:.0f} ms",
                        detail=f"Possible routing bottleneck between hop {hop_num-1} and {hop_num}"
                    ))
                    score -= 8
                    break  # report first spike only

            # Excessive hop count
            if len(hops) > 20:
                result.problems.append(Problem(
                    severity="info", module="traceroute",
                    description=f"Long route: {len(hops)} hops",
                    detail="Traffic may be taking a suboptimal path"
                ))
                score -= 5

        result.module_scores["traceroute"] = max(0, score)

    def _analyze_ports(self, payload: DiagnosticPayload, result: ProcessedResult) -> None:
        port_data = payload.results.get("port")
        if not port_data:
            return

        score = WEIGHTS["port"]
        ports = port_data.get("ports", {})

        critical_closed = []
        for port_str, info in ports.items():
            port = int(port_str)
            status = info.get("status", "UNKNOWN")
            if status == "CLOSED":
                if port in (80, 443):
                    critical_closed.append(port)

        if critical_closed:
            svc_names = {80: "HTTP", 443: "HTTPS"}
            for p in critical_closed:
                result.problems.append(Problem(
                    severity="warning", module="port",
                    description=f"Port {p} ({svc_names[p]}) is CLOSED",
                    detail=f"{svc_names[p]} service may be unavailable"
                ))
                score -= 8

        result.module_scores["port"] = max(0, score)

    # ── Scoring & status ────────────────────────────────────────────────────

    def _compute_score(self, result: ProcessedResult) -> int:
        if not result.module_scores:
            return 50
        total_possible = sum(
            WEIGHTS[k] for k in result.module_scores if k in WEIGHTS
        )
        if total_possible == 0:
            return 50
        earned = sum(result.module_scores.values())
        return round(min(100, (earned / total_possible) * 100))

    def _status_from_score(self, score: int) -> str:
        if score >= 85:
            return "HEALTHY"
        elif score >= 60:
            return "WARNING"
        elif score >= 1:
            return "CRITICAL"
        return "UNKNOWN"

    # ── Cause & recommendation builder ─────────────────────────────────────

    def _build_causes_and_recs(self, result: ProcessedResult) -> None:
        modules_with_issues = {p.module for p in result.problems}

        if "ping" in modules_with_issues and "traceroute" in modules_with_issues:
            result.possible_causes.append("ISP routing congestion or intermediate network issue")
        if "ping" in modules_with_issues and "dns" not in modules_with_issues:
            result.possible_causes.append("Remote host throttling or firewall blocking ICMP")
        if "dns" in modules_with_issues:
            result.possible_causes.append("DNS server misconfiguration or unreachable DNS resolver")
        if "port" in modules_with_issues:
            result.possible_causes.append("Firewall or service configuration blocking specific ports")
        if not modules_with_issues:
            result.possible_causes.append("No significant issues found")

        # Recommendations
        any_critical = any(p.severity == "critical" for p in result.problems)
        any_warn     = any(p.severity == "warning"  for p in result.problems)

        if any_critical:
            result.recommendations.append("Check physical/Wi-Fi connectivity and restart your router")
            result.recommendations.append("Contact your ISP if local network appears fine")
        if any_warn:
            result.recommendations.append("Try a different DNS server (e.g., 8.8.8.8 or 1.1.1.1)")
            result.recommendations.append("Run the diagnostic again at a different time to rule out transient congestion")
        if "traceroute" in modules_with_issues:
            result.recommendations.append("Compare the route at a different time — the bottleneck hop may be temporary")
        if not result.problems:
            result.recommendations.append("No action required — network is healthy")
