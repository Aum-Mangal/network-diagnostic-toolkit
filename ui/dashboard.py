"""
dashboard.py — Phase 10 & 11: Rich terminal dashboard + ASCII/matplotlib graphs.

Renders the diagnostic results using the 'rich' library for styled tables,
panels, and progress bars, plus optional matplotlib graphs.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.rule import Rule
from rich.progress import track

from core.result_processor import ProcessedResult, Problem
from core.diagnostic_engine import DiagnosticPayload

console = Console(highlight=False, force_terminal=True)

# Safe Unicode/emoji helpers (fallback for narrow Windows terminals)
def _icon(emoji: str, fallback: str) -> str:
    """Return emoji on modern terminals, ASCII fallback otherwise."""
    try:
        emoji.encode(console.file.encoding if hasattr(console, "file") else "utf-8")
        return emoji
    except (UnicodeEncodeError, AttributeError):
        return fallback

OK  = "[OK]"
WARN= "[!!]"
ERR = "[XX]"


# ── Entry point ─────────────────────────────────────────────────────────────

def render_dashboard(processed: ProcessedResult) -> None:
    """Render the full diagnostic dashboard to the terminal."""
    payload = processed.payload

    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]NETWORK DIAGNOSTIC TOOLKIT[/bold cyan]\n"
            f"[dim]Target: [white]{payload.target}[/white]   "
            f"Resolved: [white]{payload.resolved_ip}[/white]   "
            f"Intent: [white]{payload.intent}[/white][/dim]",
            border_style="cyan",
        )
    )
    console.print()

    # Validation banner
    _render_validation_banner(payload)

    # Section: Connectivity / Ping
    if "ping" in payload.results:
        _render_ping(payload.results["ping"])

    # Section: DNS
    if "dns" in payload.results:
        _render_dns(payload.results["dns"])

    # Section: Traceroute
    if "traceroute" in payload.results:
        _render_traceroute(payload.results["traceroute"])

    # Section: Ports
    if "port" in payload.results:
        _render_ports(payload.results["port"])

    # Section: Local Network
    if "network_info" in payload.results:
        _render_network_info(payload.results["network_info"])

    # Diagnosis
    _render_diagnosis(processed)

    console.print()


# ── Section renderers ────────────────────────────────────────────────────────

def _render_validation_banner(payload: DiagnosticPayload) -> None:
    dns = payload.results.get("dns", {})
    success = dns.get("success", True)
    icon = "🟢" if success else "🔴"
    console.print(Rule(f"[bold]{icon} INPUT VALIDATION[/bold]", style="white"))
    console.print(f"  Input      : [cyan]{payload.target}[/cyan]")
    console.print(f"  Resolved   : [green]{payload.resolved_ip}[/green]")
    if dns:
        t = dns.get("response_time_ms", 0)
        console.print(f"  DNS Time   : [yellow]{t:.1f} ms[/yellow]")
    console.print()


def _render_ping(ping: Dict[str, Any]) -> None:
    status = ping.get("status", "UNKNOWN")
    color = {"HEALTHY": "green", "DEGRADED": "yellow", "UNREACHABLE": "red"}.get(status, "white")
    icon  = {"HEALTHY": "🟢", "DEGRADED": "🟡", "UNREACHABLE": "🔴"}.get(status, "⚪")

    console.print(Rule(f"[bold]{icon} CONNECTIVITY (PING)[/bold]", style=color))

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Key",   style="dim",   min_width=18)
    table.add_column("Value", style="white")

    table.add_row("Target",       ping.get("target", "-"))
    table.add_row("Packets Sent", str(ping.get("sent", 0)))
    table.add_row("Received",     str(ping.get("received", 0)))
    loss = ping.get("packet_loss", 0)
    loss_color = "green" if loss == 0 else ("yellow" if loss < 10 else "red")
    table.add_row("Packet Loss",  f"[{loss_color}]{loss}%[/{loss_color}]")
    table.add_row("Min Latency",  f"{ping.get('min_latency', 0):.1f} ms")
    table.add_row("Avg Latency",  f"{ping.get('avg_latency', 0):.1f} ms")
    table.add_row("Max Latency",  f"{ping.get('max_latency', 0):.1f} ms")
    table.add_row("Status",       f"[{color}]{status}[/{color}]")

    console.print(table)

    # ASCII latency sparkline
    raw = ping.get("raw_times", [])
    if raw:
        _render_latency_sparkline(raw)
    console.print()


def _render_dns(dns: Dict[str, Any]) -> None:
    success = dns.get("success", False)
    icon    = "🟢" if success else "🔴"
    color   = "green" if success else "red"
    console.print(Rule(f"[bold]{icon} DNS RESOLUTION[/bold]", style=color))

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Key",   style="dim",   min_width=18)
    table.add_column("Value", style="white")

    table.add_row("Domain",       dns.get("domain", "-"))
    table.add_row("Status",       f"[{color}]{'SUCCESS' if success else 'FAILED'}[/{color}]")
    table.add_row("Response Time",f"{dns.get('response_time_ms', 0):.1f} ms")
    for ip in dns.get("ipv4_addresses", []):
        table.add_row("IPv4",     ip)
    for ip in dns.get("ipv6_addresses", []):
        table.add_row("IPv6",     ip)
    if not success:
        table.add_row("Error",    f"[red]{dns.get('error', '')}[/red]")

    console.print(table)
    console.print()


def _render_traceroute(tr: Dict[str, Any]) -> None:
    hops = tr.get("hops", [])
    reached = tr.get("reached", False)
    icon = "🟢" if reached else "🟡"
    console.print(Rule(f"[bold]{icon} TRACEROUTE[/bold]", style="cyan"))

    if not hops:
        console.print("  [yellow]No hops returned (firewall may block ICMP)[/yellow]\n")
        return

    table = Table(box=box.SIMPLE, padding=(0, 1))
    table.add_column("Hop",      style="dim",    width=5,  justify="right")
    table.add_column("IP",       style="cyan",   min_width=16)
    table.add_column("Hostname", style="white",  min_width=20)
    table.add_column("Latency",  style="yellow", min_width=12)
    table.add_column("Bar",      style="green",  min_width=20)

    max_lat = max(
        (h["latency_ms"] for h in hops if h.get("latency_ms") is not None), default=1
    )

    for h in hops:
        lat = h.get("latency_ms")
        ip  = h.get("ip") or "*"
        hn  = h.get("hostname") or "-"
        if hn == ip:
            hn = "-"

        if h.get("timed_out"):
            table.add_row(str(h["hop"]), "*", "*", "  *  ", "")
        else:
            bar = _make_bar(lat, max_lat, width=20) if lat is not None else ""
            lat_str = f"{lat:.1f} ms" if lat is not None else "  *  "
            table.add_row(str(h["hop"]), ip, hn, lat_str, bar)

    console.print(table)

    # ASCII path visualization
    _render_traceroute_path(hops)
    console.print()


def _render_ports(port_data: Dict[str, Any]) -> None:
    ports = port_data.get("ports", {})
    console.print(Rule(f"[bold]🔌 PORT SCAN[/bold]", style="magenta"))

    table = Table(box=box.SIMPLE, padding=(0, 2))
    table.add_column("Port",    style="cyan",  width=8)
    table.add_column("Service", style="white", min_width=12)
    table.add_column("Status",  min_width=10)

    for port_str in sorted(ports.keys(), key=int):
        info    = ports[port_str]
        status  = info.get("status", "UNKNOWN")
        service = info.get("service", "UNKNOWN")
        color   = "green" if status == "OPEN" else "red"
        icon    = "🟢" if status == "OPEN" else "🔴"
        table.add_row(port_str, service, f"[{color}]{icon} {status}[/{color}]")

    console.print(table)
    console.print()


def _render_network_info(info: Dict[str, Any]) -> None:
    console.print(Rule("[bold]🖥️  LOCAL NETWORK INFO[/bold]", style="blue"))

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Key",   style="dim",   min_width=20)
    table.add_column("Value", style="white")

    table.add_row("Hostname",        info.get("hostname", "-"))
    table.add_row("Local IP",        info.get("local_ip", "-"))
    table.add_row("Subnet Mask",     info.get("subnet_mask") or "-")
    table.add_row("Default Gateway", info.get("default_gateway") or "-")
    dns = ", ".join(info.get("dns_servers", []))
    table.add_row("DNS Servers",     dns or "-")

    console.print(table)
    console.print()


def _render_diagnosis(processed: ProcessedResult) -> None:
    score  = processed.health_score
    status = processed.overall_status
    emoji  = processed.status_emoji
    color  = {"HEALTHY": "green", "WARNING": "yellow", "CRITICAL": "red", "UNKNOWN": "white"}.get(status, "white")

    console.print(Rule(f"[bold]{emoji} DIAGNOSIS[/bold]", style=color))

    # Health score bar
    bar_filled = int(score / 5)
    bar = f"[{'green' if score >= 85 else 'yellow' if score >= 60 else 'red'}]"
    bar += "█" * bar_filled + "░" * (20 - bar_filled) + "[/]"
    console.print(f"  Health Score: {bar}  [{color}]{score}/100[/{color}]  [{color}]{status}[/{color}]")
    console.print()

    # Problems
    if processed.problems:
        console.print("  [bold]Problems Detected:[/bold]")
        sev_color = {"critical": "red", "warning": "yellow", "info": "cyan"}
        for i, p in enumerate(processed.problems, 1):
            c = sev_color.get(p.severity, "white")
            console.print(f"    {i}. [{c}][{p.severity.upper()}][/{c}] {p.description}")
            if p.detail:
                console.print(f"       [dim]{p.detail}[/dim]")
        console.print()
    else:
        console.print("  [green]✓ No significant problems detected.[/green]\n")

    # Causes
    if processed.possible_causes:
        console.print("  [bold]Possible Causes:[/bold]")
        for cause in processed.possible_causes:
            console.print(f"    • {cause}")
        console.print()

    # Recommendations
    if processed.recommendations:
        console.print("  [bold]Recommendations:[/bold]")
        for rec in processed.recommendations:
            console.print(f"    → {rec}")
        console.print()


# ── ASCII helpers ────────────────────────────────────────────────────────────

def _make_bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val == 0:
        return ""
    filled = int((value / max_val) * width)
    return "█" * filled + "░" * (width - filled)


def _render_latency_sparkline(times: List[float]) -> None:
    if not times:
        return
    max_t = max(times) or 1
    chars = " ▁▂▃▄▅▆▇█"
    spark = "".join(chars[min(8, int((t / max_t) * 8))] for t in times)
    console.print(f"  [dim]Latency trend: [yellow]{spark}[/yellow]   "
                  f"(min={min(times):.0f} avg={sum(times)/len(times):.0f} max={max(times):.0f} ms)[/dim]")


def _render_traceroute_path(hops: List[Dict[str, Any]]) -> None:
    """ASCII art path showing each hop."""
    console.print()
    console.print("  [dim]Route:[/dim]")
    console.print("  [cyan]YOUR PC[/cyan]")
    for h in hops:
        ip  = h.get("ip") or "*"
        lat = h.get("latency_ms")
        lat_str = f"  {lat:.0f}ms" if lat is not None else ""
        console.print(f"  [dim]│[/dim][yellow]{lat_str}[/yellow]")
        if h.get("timed_out"):
            console.print(f"  [dim]↓ * (timed out)[/dim]")
        else:
            hn = h.get("hostname")
            label = hn if hn and hn != ip else ip
            console.print(f"  [cyan]↓ {label}[/cyan]")


# ── Matplotlib graphs (Phase 11) ─────────────────────────────────────────────

def plot_graphs(processed: ProcessedResult) -> None:
    """Generate and save matplotlib graphs. Requires matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        console.print("[yellow]matplotlib not installed — skipping graphs.[/yellow]")
        return

    payload = processed.payload
    figures_saved = []

    # 1. Ping latency graph
    ping = payload.results.get("ping", {})
    raw_times = ping.get("raw_times", [])
    if raw_times:
        fig, ax = plt.subplots(figsize=(8, 4))
        x = list(range(1, len(raw_times) + 1))
        ax.plot(x, raw_times, marker="o", linewidth=2, color="#00BFFF", label="RTT")
        ax.axhline(ping.get("avg_latency", 0), color="orange", linestyle="--", label=f"Avg {ping.get('avg_latency',0):.1f}ms")
        ax.set_title(f"Ping Latency — {payload.target}")
        ax.set_xlabel("Ping #")
        ax.set_ylabel("Latency (ms)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        path = f"ping_latency_{payload.target.replace('.','_')}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        figures_saved.append(path)

    # 2. Traceroute hop latency bar chart
    tr = payload.results.get("traceroute", {})
    hops = [h for h in tr.get("hops", []) if h.get("latency_ms") is not None]
    if hops:
        fig, ax = plt.subplots(figsize=(10, 5))
        hop_nums = [h["hop"] for h in hops]
        latencies = [h["latency_ms"] for h in hops]
        colors = []
        prev = 0.0
        for lat in latencies:
            delta = lat - prev
            colors.append("#FF4444" if delta > 50 else "#44CC88")
            prev = lat
        bars = ax.barh(hop_nums, latencies, color=colors)
        ax.set_xlabel("Latency (ms)")
        ax.set_ylabel("Hop")
        ax.set_title(f"Traceroute Hop Latency — {payload.target}")
        ax.invert_yaxis()
        ax.grid(True, axis="x", alpha=0.3)
        good_patch = mpatches.Patch(color="#44CC88", label="Normal")
        spike_patch = mpatches.Patch(color="#FF4444", label="Spike (>50ms delta)")
        ax.legend(handles=[good_patch, spike_patch])
        path = f"traceroute_{payload.target.replace('.','_')}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        figures_saved.append(path)

    # 3. Packet loss pie chart
    if ping:
        received = ping.get("received", 0)
        lost = ping.get("lost", 0)
        if received + lost > 0:
            fig, ax = plt.subplots(figsize=(5, 5))
            ax.pie(
                [received, lost] if lost > 0 else [received],
                labels=["Received", "Lost"] if lost > 0 else ["Received"],
                colors=["#44CC88", "#FF4444"] if lost > 0 else ["#44CC88"],
                autopct="%1.1f%%",
                startangle=140,
            )
            ax.set_title(f"Packet Loss — {payload.target}")
            path = f"packet_loss_{payload.target.replace('.','_')}.png"
            fig.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            figures_saved.append(path)

    for f in figures_saved:
        console.print(f"  [green]Graph saved:[/green] {f}")
