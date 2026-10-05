"""
main.py — Network Diagnostic Toolkit
Entry point. Supports interactive mode, NL queries, and CLI flags.

Usage examples
──────────────
  python main.py                           # interactive mode
  python main.py google.com               # full scan (positional)
  python main.py "Why is google.com slow?" # natural-language query
  python main.py google.com --intent ping  # specific module
  python main.py google.com --ports 22 80 443 --save txt
  python main.py google.com --graphs
  python main.py google.com --save json --save txt
"""

from __future__ import annotations

import argparse
import sys
import os
from typing import List, Optional

# Force UTF-8 output on Windows to support Unicode characters
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.prompt import Prompt

console = Console(highlight=False, force_terminal=True)

# ── Banner ───────────────────────────────────────────────────────────────────
BANNER = r"""
  _   _      _                      _    ____  _             
 | \ | | ___| |___      _____  _ __| | _|  _ \(_) __ _  __ _ 
 |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / | | | |/ _` |/ _` |
 | |\  |  __/ |_ \ V  V / (_) | |  |   <| |_| | | (_| | (_| |
 |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\____/|_|\__,_|\__, |
                                                         |___/ 
        T O O L K I T   —   Network Diagnostic Suite
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Network Diagnostic Toolkit — Diagnose any host or IP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "query", nargs="?", default=None,
        help="Target hostname/IP or natural-language query (e.g. 'Why is google.com slow?')"
    )
    parser.add_argument(
        "--intent", default=None,
        choices=["full", "connectivity", "performance", "slow", "access",
                 "https", "http", "ssh", "dns", "route"],
        help="Force a specific diagnostic intent (overrides NL detection)",
    )
    parser.add_argument(
        "--ports", nargs="+", type=int, default=None,
        metavar="PORT",
        help="Custom port list for port scan (e.g. --ports 22 80 443)",
    )
    parser.add_argument(
        "--count", type=int, default=4,
        help="Number of ping packets (default: 4)",
    )
    parser.add_argument(
        "--save", nargs="+", choices=["txt", "json"], default=None,
        metavar="FORMAT",
        help="Save report in one or more formats: txt, json",
    )
    parser.add_argument(
        "--graphs", action="store_true",
        help="Generate matplotlib graphs (requires matplotlib)",
    )
    parser.add_argument(
        "--no-banner", action="store_true",
        help="Suppress the ASCII banner",
    )

    args = parser.parse_args()

    if not args.no_banner:
        console.print(f"[cyan]{BANNER}[/cyan]")

    # ── Get query ─────────────────────────────────────────────────────────
    raw_query = args.query
    if not raw_query:
        raw_query = Prompt.ask(
            "[bold cyan]Enter domain / IP / query[/bold cyan]\n"
            "[dim](e.g. google.com  or  'Why is google.com slow?')[/dim]\n> "
        ).strip()
        if not raw_query:
            console.print("[red]No input provided. Exiting.[/red]")
            sys.exit(1)

    # ── NL parsing ────────────────────────────────────────────────────────
    from analysis.diagnosis import parse_query
    parsed = parse_query(raw_query)

    target = parsed.target or raw_query
    intent = args.intent or parsed.intent

    if parsed.natural_language:
        console.print(f"\n[dim]Interpreted: target=[cyan]{target}[/cyan]  intent=[cyan]{intent}[/cyan][/dim]\n")

    # ── Validate ──────────────────────────────────────────────────────────
    from core.validator import validate
    console.print(f"[dim]Validating [cyan]{target}[/cyan] …[/dim]")
    validation = validate(target)

    if not validation.is_valid:
        console.print(f"[red]✗ {validation.error}[/red]")
        sys.exit(1)

    console.print(f"[green]OK Valid {validation.input_type}[/green]  ->  [cyan]{validation.resolved_ip}[/cyan]  "
                  f"[dim]({validation.resolution_time_ms:.1f} ms)[/dim]\n")

    # ── Diagnostics ───────────────────────────────────────────────────────
    from core.diagnostic_engine import DiagnosticEngine
    engine = DiagnosticEngine(validation)

    console.print(f"[dim]Running diagnostics  [intent=[cyan]{intent}[/cyan]] …[/dim]\n")
    payload = engine.run(
        intent=intent,
        custom_ports=args.ports,
        ping_count=args.count,
    )

    # ── Process results ───────────────────────────────────────────────────
    from core.result_processor import ResultProcessor
    processor = ResultProcessor()
    processed = processor.process(payload)

    # ── Render dashboard ──────────────────────────────────────────────────
    from ui.dashboard import render_dashboard, plot_graphs
    render_dashboard(processed)

    # ── Graphs ────────────────────────────────────────────────────────────
    if args.graphs:
        console.print("[dim]Generating graphs …[/dim]")
        plot_graphs(processed)

    # ── Save reports ──────────────────────────────────────────────────────
    if args.save:
        from reports.report_generator import save_report
        for fmt in args.save:
            path = save_report(processed, fmt=fmt)
            console.print(f"[green]Report saved:[/green] {path}")

    console.print(f"\n[dim]Total diagnostic time: {payload.total_time_ms:.0f} ms[/dim]\n")


if __name__ == "__main__":
    main()
