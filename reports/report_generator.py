"""
report_generator.py — Phase 14: Text / JSON / PDF Report Generator

Produces a formatted diagnostic report from a ProcessedResult.
Supports three output formats: txt (plain text), json, and pdf (requires reportlab).
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
    sep  = "═" * 54
    dash = "─" * 54

    lines += [sep, " NETWORK DIAGNOSTIC REPORT", sep, ""]
    lines += [f" Generated : {now}",
              f" Target    : {p.target}",
              f" Resolved  : {p.resolved_ip}",
              f" Intent    : {p.intent}", ""]

    # Connectivity
    if "ping" in p.results:
        ping = p.results["ping"]
        lines += [dash, " CONNECTIVITY (PING)", dash,
                  f" Status       : {ping.get('status', '-')}",
                  f" Latency      : {ping.get('avg_latency', 0):.1f} ms",
                  f" Packet Loss  : {ping.get('packet_loss', 0):.1f}%",
                  f" Sent/Recv    : {ping.get('sent', 0)}/{ping.get('received', 0)}", ""]

    # DNS
    if "dns" in p.results:
        dns = p.results["dns"]
        lines += [dash, " DNS", dash,
                  f" Status       : {'SUCCESS' if dns.get('success') else 'FAILED'}",
                  f" Resolved IP  : {', '.join(dns.get('ipv4_addresses', []) or ['-'])}",
                  f" Response Time: {dns.get('response_time_ms', 0):.1f} ms", ""]

    # Traceroute
    if "traceroute" in p.results:
        tr = p.results["traceroute"]
        hops = tr.get("hops", [])
        lines += [dash, " ROUTE (TRACEROUTE)", dash,
                  f" Total Hops   : {tr.get('total_hops', 0)}",
                  f" Reached      : {'YES' if tr.get('reached') else 'NO'}", ""]
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
        lines += [dash, " PORT SCAN", dash,
                  f"  {'Port':<8} {'Service':<14} {'Status'}"]
        lines.append(f"  {'-'*8} {'-'*14} {'-'*8}")
        for port_str in sorted(port_data.get("ports", {}).keys(), key=int):
            info = port_data["ports"][port_str]
            lines.append(f"  {port_str:<8} {info['service']:<14} {info['status']}")
        lines.append("")

    # Local network
    if "network_info" in p.results:
        ni = p.results["network_info"]
        lines += [dash, " LOCAL NETWORK", dash,
                  f" Hostname       : {ni.get('hostname', '-')}",
                  f" Local IP       : {ni.get('local_ip', '-')}",
                  f" Subnet Mask    : {ni.get('subnet_mask') or '-'}",
                  f" Default Gateway: {ni.get('default_gateway') or '-'}",
                  f" DNS Servers    : {', '.join(ni.get('dns_servers', []))}", ""]

    # Diagnosis
    lines += [sep, " FINAL DIAGNOSIS", sep,
              f" Health Score : {processed.health_score}/100",
              f" Status       : {processed.status_emoji} {processed.overall_status}", ""]

    if processed.problems:
        lines.append(" Problems:")
        for i, prob in enumerate(processed.problems, 1):
            lines.append(f"   {i}. [{prob.severity.upper()}] {prob.description}")
            if prob.detail:
                lines.append(f"      {prob.detail}")
        lines.append("")

    if processed.possible_causes:
        lines.append(" Possible Causes:")
        for c in processed.possible_causes:
            lines.append(f"   • {c}")
        lines.append("")

    if processed.recommendations:
        lines.append(" Recommendations:")
        for r in processed.recommendations:
            lines.append(f"   → {r}")
        lines.append("")

    lines.append(sep)
    return "\n".join(lines)


# ── JSON report ──────────────────────────────────────────────────────────────

def generate_json_report(processed: ProcessedResult) -> str:
    """Return the full diagnostic data as a JSON string."""
    p = processed.payload
    data: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "target":       p.target,
        "resolved_ip":  p.resolved_ip,
        "intent":       p.intent,
        "health_score": processed.health_score,
        "status":       processed.overall_status,
        "modules_run":  p.modules_run,
        "results":      p.results,
        "problems": [
            {
                "severity":    prob.severity,
                "module":      prob.module,
                "description": prob.description,
                "detail":      prob.detail,
            }
            for prob in processed.problems
        ],
        "possible_causes":  processed.possible_causes,
        "recommendations":  processed.recommendations,
        "total_time_ms":    p.total_time_ms,
    }
    return json.dumps(data, indent=2, default=str)


# ── Save helpers ─────────────────────────────────────────────────────────────

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
    safe_target = processed.payload.target.replace(".", "_").replace(":", "_")
    filename = f"report_{safe_target}_{timestamp}.{fmt}"
    filepath = os.path.join(output_dir, filename)

    if fmt == "json":
        content = generate_json_report(processed)
    else:
        content = generate_txt_report(processed)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath
