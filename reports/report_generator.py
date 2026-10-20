"""
report_generator.py — Phase 14: Text & JSON Report Generator

Produces a formatted diagnostic report from a ProcessedResult.
Supports two clean output formats:
  - txt: Plain-text report formatted for terminal, logs, or printing.
  - json: Machine-readable structured payload for CI/CD or APIs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict

from core.result_processor import ProcessedResult
from core.diagnostic_engine import DiagnosticPayload


# ── TXT report ───────────────────────────────────────────────────────────────

def generate_txt_report(processed: ProcessedResult) -> str:
    """Return the full text report as a string."""
    p = processed.payload
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    sep  = "═" * 60
    dash = "─" * 60

    lines += [sep, " NETWORK DIAGNOSTIC REPORT", sep, ""]
    lines += [
        f" Generated   : {now}",
        f" Target      : {p.target}",
        f" Resolved IP : {p.resolved_ip or '-'}",
        f" Intent      : {p.intent}",
        f" Overall     : {processed.status_emoji} {processed.overall_status} (Score: {processed.health_score}/100)",
        ""
    ]

    if processed.joint_root_cause:
        lines += [
            dash, " SYNTHESIZED ROOT-CAUSE DIAGNOSIS", dash,
            f" {processed.joint_root_cause}", ""
        ]

    # Connectivity
    if "ping" in p.results:
        ping = p.results["ping"]
        lines += [
            dash, " CONNECTIVITY (PING)", dash,
            f" Status       : {ping.get('status', '-')}",
            f" Latency      : {ping.get('avg_latency', 0):.1f} ms (min: {ping.get('min_latency', 0):.1f} / max: {ping.get('max_latency', 0):.1f})",
            f" Packet Loss  : {ping.get('packet_loss', 0):.1f}%",
            f" Packets      : Sent {ping.get('sent', 0)} | Received {ping.get('received', 0)}",
            ""
        ]

    # DNS
    if "dns" in p.results:
        dns = p.results["dns"]
        lines += [
            dash, " DNS RESOLUTION", dash,
            f" Status       : {'SUCCESS' if dns.get('success') else 'FAILED'}",
            f" IPv4 Records : {', '.join(dns.get('ipv4_addresses', []) or ['-'])}",
            f" IPv6 Records : {', '.join(dns.get('ipv6_addresses', []) or ['None'])}",
            f" Lookup Time  : {dns.get('response_time_ms', 0):.1f} ms",
            ""
        ]

    # Traceroute
    if "traceroute" in p.results:
        tr = p.results["traceroute"]
        hops = tr.get("hops", [])
        lines += [
            dash, " ROUTING (TRACEROUTE)", dash,
            f" Total Hops   : {tr.get('total_hops', 0)}",
            f" Reached      : {'YES' if tr.get('reached') else 'NO'}",
            ""
        ]
        lines.append(f"  {'Hop':<5} {'IP':<18} {'Hostname':<22} {'Latency':>10}")
        lines.append(f"  {'-'*5} {'-'*18} {'-'*22} {'-'*10}")
        for h in hops:
            ip  = h.get("ip") or "*"
            hn  = (h.get("hostname") or "-")[:20]
            lat = f"{h['latency_ms']:.1f} ms" if h.get("latency_ms") else "   *"
            lines.append(f"  {h['hop']:<5} {ip:<18} {hn:<22} {lat:>10}")
        lines.append("")

    # Ports
    if "port" in p.results:
        port_data = p.results["port"]
        ports_map = port_data.get("ports", {})
        lines += [
            dash, " PORT ACCESSIBILITY", dash,
            f" Open Ports   : {port_data.get('open_count', 0)}",
            ""
        ]
        lines.append(f"  {'Port':<8} {'Service':<16} {'Status':<10}")
        lines.append(f"  {'-'*8} {'-'*16} {'-'*10}")
        for p_num in sorted(ports_map.keys(), key=int):
            info = ports_map[p_num]
            lines.append(f"  {p_num:<8} {info['service']:<16} {info['status']:<10}")
        lines.append("")

    # Local Network
    if "network_info" in p.results:
        net = p.results["network_info"]
        lines += [
            dash, " LOCAL NETWORK CONTEXT", dash,
            f" Hostname     : {net.get('hostname', '-')}",
            f" Local IP     : {net.get('local_ip', '-')}",
            f" Gateway      : {net.get('default_gateway', '-')}",
            f" DNS Servers  : {', '.join(net.get('dns_servers', []) or ['-'])}",
            ""
        ]

    # Explainable Problems with Measurements & Thresholds
    if processed.problems:
        lines += [dash, " DETECTED PROBLEMS & EXPLANATIONS", dash]
        for prob in processed.problems:
            lines.append(f" • [{prob.severity.upper()}] {prob.description}")
            if prob.measurement:
                lines.append(f"   Measured   : {prob.measurement}")
            if prob.threshold:
                lines.append(f"   Threshold  : {prob.threshold}")
            if prob.explanation:
                lines.append(f"   Explanation: {prob.explanation}")
            lines.append("")

    # Recommendations
    if processed.recommendations:
        lines += [dash, " ACTIONABLE RECOMMENDATIONS", dash]
        for rec in processed.recommendations:
            lines.append(f" → {rec}")
        lines.append("")

    lines += [sep, f" Execution Time: {p.total_time_ms:.0f} ms", sep]
    return "\n".join(lines)


# ── JSON report ──────────────────────────────────────────────────────────────

def generate_json_report(processed: ProcessedResult) -> str:
    """Return the full diagnostic data as a formatted JSON string."""
    p = processed.payload
    data: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "target":       p.target,
        "resolved_ip":  p.resolved_ip,
        "intent":       p.intent,
        "health_score": processed.health_score,
        "status":       processed.overall_status,
        "root_cause":   processed.joint_root_cause,
        "modules_run":  p.modules_run,
        "results":      p.results,
        "problems": [
            {
                "severity":    prob.severity,
                "module":      prob.module,
                "description": prob.description,
                "detail":      prob.detail,
                "measurement": prob.measurement,
                "threshold":   prob.threshold,
                "rule":        prob.rule,
                "explanation": prob.explanation,
            }
            for prob in processed.problems
        ],
        "possible_causes":  processed.possible_causes,
        "recommendations":  processed.recommendations,
        "total_time_ms":    p.total_time_ms,
    }
    return json.dumps(data, indent=2, default=str)


# ── Save helper ──────────────────────────────────────────────────────────────

def save_report(
    processed: ProcessedResult,
    fmt: str = "txt",
    output_dir: str = ".",
) -> str:
    """
    Save the report in the given format ('txt' or 'json').
    Returns the path of the saved file.
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_target = processed.payload.target.replace(".", "_").replace(":", "_").replace("/", "_")
    filename = f"report_{safe_target}_{timestamp}.{fmt}"
    filepath = os.path.join(output_dir, filename)

    if fmt == "json":
        content = generate_json_report(processed)
    else:
        content = generate_txt_report(processed)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath
