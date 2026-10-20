"""
result_processor.py — Phase 8 & 9: Analysis, Scoring & Diagnostic Rules Engine

Takes the raw DiagnosticPayload and produces human-readable analysis,
a numeric health score, explainable problems with measurements and thresholds,
possible root causes, and actionable recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.diagnostic_engine import DiagnosticPayload


# ── Scoring weights ─────────────────────────────────────────────────────────
WEIGHTS = {
    "ping":         40,
    "dns":          20,
    "traceroute":   20,
    "port":         10,
    "network_info": 10,
}

# ── Latency thresholds (ms) ─────────────────────────────────────────────────
LATENCY_EXCELLENT = 50.0
LATENCY_GOOD      = 100.0
LATENCY_WARN      = 200.0

# ── Packet loss thresholds (%) ──────────────────────────────────────────────
LOSS_WARN     = 5.0
LOSS_HIGH     = 10.0
LOSS_CRITICAL = 30.0

# ── Hop-latency spike threshold ─────────────────────────────────────────────
HOP_SPIKE_MS = 50.0   # delta that counts as a routing bottleneck


@dataclass
class Problem:
    severity: str          # "info" | "warning" | "critical"
    module: str
    description: str
    detail: str = ""
    measurement: str = ""  # e.g. "avg_latency = 142.3 ms"
    threshold: str = ""    # e.g. "< 100.0 ms"
    rule: str = ""         # e.g. "IF avg_latency > 100ms THEN Warning"
    explanation: str = ""  # Detailed technical rationale


@dataclass
class ProcessedResult:
    payload: DiagnosticPayload
    health_score: int                   # 0–100
    overall_status: str                 # "HEALTHY" | "WARNING" | "CRITICAL" | "UNKNOWN"
    problems: List[Problem] = field(default_factory=list)
    possible_causes: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    module_scores: Dict[str, int] = field(default_factory=dict)
    joint_root_cause: str = ""          # Clear synthesized diagnosis statement

    @property
    def status_emoji(self) -> str:
        return {"HEALTHY": "🟢", "WARNING": "🟡", "CRITICAL": "🔴", "UNKNOWN": "⚪"}.get(
            self.overall_status, "⚪"
        )


class ResultProcessor:
    """Applies the diagnostic rules engine to a DiagnosticPayload."""

    def process(self, payload: DiagnosticPayload) -> ProcessedResult:
        result = ProcessedResult(payload=payload, health_score=0, overall_status="UNKNOWN")

        # 1. Process module errors first (honest reporting of failed checks)
        self._analyze_errors(payload, result)

        # 2. Analyze individual modules
        self._analyze_ping(payload, result)
        self._analyze_dns(payload, result)
        self._analyze_traceroute(payload, result)
        self._analyze_ports(payload, result)
        self._analyze_network_info(payload, result)

        # 3. Compute score and status
        result.health_score = self._compute_score(payload, result)
        result.overall_status = self._status_from_score(result.health_score)

        # 4. Synthesize joint root-cause and actionable recommendations
        self._synthesize_diagnosis(result)

        return result

    # ── Module error analyzer ───────────────────────────────────────────────

    def _analyze_errors(self, payload: DiagnosticPayload, result: ProcessedResult) -> None:
        """Record explicit problems for any module that crashed or failed to run."""
        for mod, err in payload.errors.items():
            base_mod = mod.split("_")[0]
            result.problems.append(Problem(
                severity="critical" if mod in ("ping", "dns") else "warning",
                module=base_mod,
                description=f"Module '{mod}' failed to execute",
                detail=err,
                measurement="Execution Status: FAILED",
                threshold="Expected: SUCCESS",
                rule=f"IF {mod}.status == ERROR THEN Critical",
                explanation=f"The {mod} module encountered an unhandled system or network error."
            ))
            result.module_scores[base_mod] = 0

    # ── Module analyzers ────────────────────────────────────────────────────

    def _analyze_ping(self, payload: DiagnosticPayload, result: ProcessedResult) -> None:
        ping = payload.results.get("ping")
        if not ping:
            return

        score = WEIGHTS["ping"]
        loss = float(ping.get("packet_loss", 0))
        avg  = float(ping.get("avg_latency", 0))
        recv = int(ping.get("received", 0))
        sent = int(ping.get("sent", 4))

        if recv == 0:
            result.problems.append(Problem(
                severity="critical",
                module="ping",
                description="Target is unreachable (100% packet loss)",
                detail=f"Sent {sent} ICMP echo requests, received 0 replies.",
                measurement=f"packets_received = 0 / {sent} (loss: 100%)",
                threshold="packets_received > 0",
                rule="IF packets_received == 0 THEN Target Unreachable",
                explanation="The destination host did not respond to ICMP Echo Requests. It may be offline, the route may be down, or a firewall is silently dropping ICMP."
            ))
            score = 0
        else:
            # Packet loss evaluation
            if loss >= LOSS_CRITICAL:
                result.problems.append(Problem(
                    severity="critical",
                    module="ping",
                    description=f"Critical packet loss detected: {loss:.1f}%",
                    detail="Severe connection instability affecting data transmission.",
                    measurement=f"packet_loss = {loss:.1f}%",
                    threshold=f"packet_loss < {LOSS_WARN}%",
                    rule=f"IF packet_loss >= {LOSS_CRITICAL}% THEN Critical Loss",
                    explanation="High packet loss indicates physical line noise, severe Wi-Fi interference, or buffer overflows on network interfaces."
                ))
                score -= 30
            elif loss >= LOSS_HIGH:
                result.problems.append(Problem(
                    severity="warning",
                    module="ping",
                    description=f"High packet loss detected: {loss:.1f}%",
                    detail="Significant packet loss causing retransmissions and jitter.",
                    measurement=f"packet_loss = {loss:.1f}%",
                    threshold=f"packet_loss < {LOSS_WARN}%",
                    rule=f"IF packet_loss >= {LOSS_HIGH}% THEN Warning Loss",
                    explanation="Elevated packet loss triggers TCP congestion avoidance, severely cutting download and upload throughput."
                ))
                score -= 20
            elif loss >= LOSS_WARN:
                result.problems.append(Problem(
                    severity="info",
                    module="ping",
                    description=f"Minor packet loss detected: {loss:.1f}%",
                    detail="Occasional drops observed.",
                    measurement=f"packet_loss = {loss:.1f}%",
                    threshold=f"packet_loss < {LOSS_WARN}%",
                    rule=f"IF packet_loss >= {LOSS_WARN}% THEN Minor Loss",
                    explanation="Slight packet loss observed during ping sample."
                ))
                score -= 8

            # Latency evaluation
            if avg > LATENCY_WARN:
                result.problems.append(Problem(
                    severity="warning",
                    module="ping",
                    description=f"High average latency: {avg:.1f} ms",
                    detail=f"Round-trip time exceeds {LATENCY_WARN} ms.",
                    measurement=f"avg_latency = {avg:.1f} ms",
                    threshold=f"avg_latency <= {LATENCY_GOOD} ms",
                    rule=f"IF avg_latency > {LATENCY_WARN}ms THEN High Latency",
                    explanation="High round-trip delay creates noticeable sluggishness in web browsing, SSH, and real-time streaming."
                ))
                score -= 15
            elif avg > LATENCY_GOOD:
                result.problems.append(Problem(
                    severity="info",
                    module="ping",
                    description=f"Elevated average latency: {avg:.1f} ms",
                    detail="Round-trip time is above optimal baseline.",
                    measurement=f"avg_latency = {avg:.1f} ms",
                    threshold=f"avg_latency <= {LATENCY_GOOD} ms",
                    rule=f"IF avg_latency > {LATENCY_GOOD}ms THEN Elevated Latency",
                    explanation="Latency is acceptable for bulk downloads, but higher than optimal for low-latency interactive applications."
                ))
                score -= 7

        result.module_scores["ping"] = max(0, score)

    def _analyze_dns(self, payload: DiagnosticPayload, result: ProcessedResult) -> None:
        dns = payload.results.get("dns")
        if not dns:
            return

        score = WEIGHTS["dns"]
        if not dns.get("success"):
            err_msg = dns.get("error", "Unknown DNS error")
            result.problems.append(Problem(
                severity="critical",
                module="dns",
                description="DNS resolution failed",
                detail=err_msg,
                measurement="dns_status = FAILED",
                threshold="dns_status == SUCCESS",
                rule="IF dns_resolution == FAILED THEN Critical DNS",
                explanation="The system cannot resolve the domain name to an IP address. Check local DNS settings or domain registration."
            ))
            score = 0
        else:
            resp_ms = float(dns.get("response_time_ms", 0))
            if resp_ms > 300:
                result.problems.append(Problem(
                    severity="warning",
                    module="dns",
                    description=f"Slow DNS resolution: {resp_ms:.1f} ms",
                    detail="DNS lookup took significantly longer than standard baseline.",
                    measurement=f"dns_response_time = {resp_ms:.1f} ms",
                    threshold="dns_response_time <= 100.0 ms",
                    rule="IF dns_response_time > 300ms THEN Slow DNS",
                    explanation="DNS queries over 100-200ms introduce perceived initial lag before websites or services begin to load."
                ))
                score -= 10
            elif resp_ms > 100:
                result.problems.append(Problem(
                    severity="info",
                    module="dns",
                    description=f"Moderate DNS response time: {resp_ms:.1f} ms",
                    detail="Resolution is functional but un-cached.",
                    measurement=f"dns_response_time = {resp_ms:.1f} ms",
                    threshold="dns_response_time <= 100.0 ms",
                    rule="IF dns_response_time > 100ms THEN Moderate DNS",
                    explanation="DNS lookup was resolved via authoritative/recursive query without local cache."
                ))
                score -= 4

        result.module_scores["dns"] = max(0, score)

    def _analyze_traceroute(self, payload: DiagnosticPayload, result: ProcessedResult) -> None:
        tr = payload.results.get("traceroute")
        if not tr:
            return

        score = WEIGHTS["traceroute"]
        hops = tr.get("hops", [])
        reached = tr.get("reached", False)

        if not hops:
            result.problems.append(Problem(
                severity="warning",
                module="traceroute",
                description="Traceroute produced no hops",
                detail="No intermediate routers returned ICMP Time-Exceeded messages.",
                measurement="total_hops = 0",
                threshold="total_hops > 0",
                rule="IF total_hops == 0 THEN Route Blocked",
                explanation="An outbound firewall or local ISP is dropping ICMP TTL-expired packets."
            ))
            score -= 10
        else:
            # 1. Distinguish RFC 1812 router rate-limiting vs real drop
            unanswered_hops = [h["hop"] for h in hops if h.get("latency_ms") is None]
            if unanswered_hops and reached:
                # Routers didn't reply to ICMP, but final destination was reached!
                result.problems.append(Problem(
                    severity="info",
                    module="traceroute",
                    description=f"ICMP rate-limiting at hop(s) {', '.join(map(str, unanswered_hops))}",
                    detail="Intermediate routers did not reply (* * *), but final destination was reached.",
                    measurement=f"unresponsive_hops = {unanswered_hops}",
                    threshold="N/A (RFC 1812 control-plane rate limiting)",
                    rule="IF hop == '*' AND target_reached THEN Rate Limiting",
                    explanation="Transit routers frequently drop ICMP TTL-Exceeded packets to protect CPU control planes (RFC 1812). This is normal network behavior and does not represent packet loss."
                ))

            # 2. Detect genuine routing bottlenecks:
            # A real bottleneck requires Hop N to jump by > HOP_SPIKE_MS AND all subsequent responding hops stay high!
            responding_hops = [h for h in hops if h.get("latency_ms") is not None]
            for i in range(1, len(responding_hops)):
                delta = responding_hops[i]["latency_ms"] - responding_hops[i - 1]["latency_ms"]
                if delta > HOP_SPIKE_MS:
                    hop_num = responding_hops[i]["hop"]
                    # Verify if subsequent hops stay high (persisting bottleneck)
                    sustained = all(
                        h["latency_ms"] >= responding_hops[i]["latency_ms"] - 20
                        for h in responding_hops[i:]
                    )
                    if sustained:
                        result.problems.append(Problem(
                            severity="warning",
                            module="traceroute",
                            description=f"Routing bottleneck confirmed at hop {hop_num}: +{delta:.0f} ms spike",
                            detail=f"Latency jumped from {responding_hops[i-1]['latency_ms']:.1f}ms to {responding_hops[i]['latency_ms']:.1f}ms and persisted through destination.",
                            measurement=f"latency_delta = +{delta:.1f} ms at hop {hop_num}",
                            threshold=f"delta <= {HOP_SPIKE_MS} ms",
                            rule=f"IF delta > {HOP_SPIKE_MS}ms AND sustained THEN Routing Bottleneck",
                            explanation="A sustained latency jump across subsequent hops indicates link saturation or routing congestion at an intermediate transit provider."
                        ))
                        score -= 10
                        break

            # 3. Excessive hop count check
            if len(hops) > 20:
                result.problems.append(Problem(
                    severity="info",
                    module="traceroute",
                    description=f"Long routing path: {len(hops)} hops",
                    detail="Traffic traverses more than 20 intermediate routers.",
                    measurement=f"hop_count = {len(hops)}",
                    threshold="hop_count <= 20",
                    rule="IF hop_count > 20 THEN Suboptimal Route",
                    explanation="Higher hop counts generally increase the probability of jitter and route instability."
                ))
                score -= 4

        result.module_scores["traceroute"] = max(0, score)

    def _analyze_ports(self, payload: DiagnosticPayload, result: ProcessedResult) -> None:
        port_data = payload.results.get("port")
        if not port_data:
            return

        score = WEIGHTS["port"]
        ports = port_data.get("ports", {})

        closed_services = []
        for port_str, info in ports.items():
            port = int(port_str)
            status = info.get("status", "UNKNOWN")
            if status == "CLOSED":
                if port in (80, 443):
                    closed_services.append((port, info.get("service", "Web")))

        if closed_services:
            for p, svc in closed_services:
                result.problems.append(Problem(
                    severity="warning",
                    module="port",
                    description=f"Port {p} ({svc}) is CLOSED",
                    detail=f"Connection refused on standard service port {p}.",
                    measurement=f"port_{p}_status = CLOSED",
                    threshold="port_status == OPEN",
                    rule=f"IF port_{p} == CLOSED THEN Service Unavailable",
                    explanation=f"The remote daemon is not listening on port {p} or a firewall is actively rejecting TCP SYN packets."
                ))
                score -= 8

        result.module_scores["port"] = max(0, score)

    def _analyze_network_info(self, payload: DiagnosticPayload, result: ProcessedResult) -> None:
        net = payload.results.get("network_info")
        if not net:
            return

        score = WEIGHTS["network_info"]
        local_ip = net.get("local_ip", "")
        gateway = net.get("default_gateway")

        # Check APIPA (169.254.x.x DHCP failure)
        if local_ip.startswith("169.254."):
            result.problems.append(Problem(
                severity="critical",
                module="network_info",
                description="APIPA Auto-configuration IP detected (169.254.x.x)",
                detail="Host could not obtain an IP address from the local DHCP server.",
                measurement=f"local_ip = {local_ip}",
                threshold="local_ip != 169.254.*",
                rule="IF ip_starts_with('169.254') THEN DHCP Failure",
                explanation="Your router or DHCP server failed to assign an IP address. Check Ethernet cable or Wi-Fi authentication."
            ))
            score -= 10

        # Check missing default gateway
        if not gateway:
            result.problems.append(Problem(
                severity="warning",
                module="network_info",
                description="No default gateway detected",
                detail="Outbound Internet routing may be unavailable.",
                measurement="default_gateway = None",
                threshold="default_gateway IS NOT None",
                rule="IF default_gateway == None THEN Gateway Missing",
                explanation="Without a default gateway, your device cannot route traffic outside the local subnet."
            ))
            score -= 6

        result.module_scores["network_info"] = max(0, score)

    # ── Scoring & status ────────────────────────────────────────────────────

    def _compute_score(self, payload: DiagnosticPayload, result: ProcessedResult) -> int:
        """
        Compute an honest score considering intended modules.
        Failed or timed-out modules contribute 0 earned out of their potential weight.
        """
        # Determine total possible weight across all modules that were supposed to run
        intended = set(payload.intended_modules) if payload.intended_modules else set(result.module_scores.keys())
        
        # Map sub-modules like port_443 to 'port'
        normalized_intended = set()
        for m in intended:
            normalized_intended.add(m.split("_")[0])

        total_possible = sum(WEIGHTS.get(k, 10) for k in normalized_intended)
        if total_possible == 0:
            return 50

        earned = sum(result.module_scores.get(k, 0) for k in normalized_intended)
        return max(0, min(100, round((earned / total_possible) * 100)))

    def _status_from_score(self, score: int) -> str:
        if score >= 85:
            return "HEALTHY"
        elif score >= 60:
            return "WARNING"
        return "CRITICAL"

    # ── Joint Synthesis & Recommendations ───────────────────────────────────

    def _synthesize_diagnosis(self, result: ProcessedResult) -> None:
        p = result.payload
        ping = p.results.get("ping")
        dns = p.results.get("dns")
        tr = p.results.get("traceroute")
        port_d = p.results.get("port")

        causes = []
        recs = []
        root_cause_parts = []

        # 1. Unreachable destination
        if ping and ping.get("received", 0) == 0:
            causes.append("Host is powered off, offline, or ICMP echo requests are blocked by a firewall.")
            recs.append("Verify destination IP is correct and test service ports (HTTP/HTTPS) using TCP port scan.")
            root_cause_parts.append("Complete ICMP packet drop to destination host.")

        # 2. Packet loss
        elif ping and ping.get("packet_loss", 0) > 0:
            causes.append("Wi-Fi interference, local cable degradation, or upstream ISP line congestion.")
            recs.append("Run ping to your default gateway to isolate whether loss is on local Wi-Fi or outside ISP.")
            root_cause_parts.append(f"{ping.get('packet_loss', 0):.1f}% packet loss observed.")

        # 3. Slow DNS vs Low ping
        if dns and dns.get("success") and dns.get("response_time_ms", 0) > 200:
            if ping and ping.get("avg_latency", 0) < 50:
                root_cause_parts.append(
                    f"DNS resolution is slow ({dns.get('response_time_ms', 0):.0f}ms), while path latency is fast ({ping.get('avg_latency', 0):.0f}ms). Switch your DNS resolver to 1.1.1.1 or 8.8.8.8."
                )
                causes.append("Configured DNS resolver is un-cached or experiencing query queue latency.")
                recs.append("Change local DNS servers to Cloudflare (1.1.1.1) or Google DNS (8.8.8.8).")

        # 4. Traceroute bottleneck
        if tr:
            bottlenecks = [prob for prob in result.problems if "Routing bottleneck" in prob.description]
            if bottlenecks:
                causes.append("Intermediate transit router / ISP peer exchange congestion.")
                recs.append("Contact network administrator or ISP regarding routing delay on the reported transit hop.")
                root_cause_parts.append(bottlenecks[0].description)

        # 5. Closed ports
        if port_d:
            ports = port_d.get("ports", {})
            for p_num, p_info in ports.items():
                if int(p_num) in (80, 443) and p_info.get("status") == "CLOSED":
                    causes.append(f"Web service daemon is stopped or firewall is blocking port {p_num}.")
                    recs.append(f"Check server web service (nginx, apache) and inbound security group rules for port {p_num}.")

        # Fallback healthy state
        if not root_cause_parts:
            if result.overall_status == "HEALTHY":
                result.joint_root_cause = "All diagnostic parameters are within optimal operating thresholds. No network degradation detected."
                recs.append("No action required. Connection to target is performing nominally.")
            else:
                result.joint_root_cause = "Minor network anomalies observed; refer to detected issues below."
        else:
            result.joint_root_cause = " | ".join(root_cause_parts)

        result.possible_causes = causes
        result.recommendations = recs
