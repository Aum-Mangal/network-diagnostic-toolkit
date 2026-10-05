# Network Diagnostic Toolkit

> A full-stack Python network diagnostics suite — Ping, DNS, Traceroute, Port Scan, local network info, smart analysis, browser GUI.

## Features
- **Phase 2** — Input validation (IPv4 / IPv6 / Domain)
- **Phase 3** — ICMP Ping with latency & packet loss parsing
- **Phase 4** — DNS resolution (A & AAAA records)
- **Phase 5** — Traceroute with per-hop latency
- **Phase 6** — TCP Port Scanner (concurrent)
- **Phase 7** — Local network info (IP, subnet, gateway, DNS)
- **Phase 8/9** — Rules engine: scoring, problem detection, recommendations
- **Phase 10/11** — Browser GUI (Streamlit + Plotly charts)
- **Phase 12/13** — Natural-language queries + smart module planner
- **Phase 14** — TXT / JSON report export

## Quick Start

```bash
pip install -r requirements.txt

# Terminal CLI
python main.py google.com

# Browser GUI
streamlit run app.py
```

## Usage

```bash
# Direct target
python main.py google.com

# Natural language
python main.py "Why is google.com slow?"

# Custom ports + save reports
python main.py google.com --ports 22 80 443 --save txt json

# Graphs
python main.py google.com --graphs
```

## Project Structure

```
network-diagnostic-toolkit/
├── main.py                  # CLI entry point
├── app.py                   # Browser GUI (Streamlit)
├── requirements.txt
├── core/
│   ├── validator.py         # Input validation & DNS resolution
│   ├── diagnostic_engine.py # Smart planner & orchestrator
│   └── result_processor.py  # Rules engine & scoring
├── modules/
│   ├── ping.py              # ICMP ping
│   ├── traceroute.py        # Traceroute
│   ├── dns_lookup.py        # DNS lookup
│   ├── port_scanner.py      # Port scanner
│   └── network_info.py      # Local network info
├── analysis/
│   ├── latency.py           # Latency analysis
│   ├── packet_loss.py       # Packet loss analysis
│   └── diagnosis.py         # NL intent parser
├── ui/
│   └── dashboard.py         # Terminal dashboard
└── reports/
    └── report_generator.py  # TXT / JSON reports
```

## Tech Stack

- Python 3.10+
- Streamlit — browser GUI
- Plotly — interactive charts
- Rich — terminal dashboard
- socket / subprocess — networking

## CN Project Info

Built as a Computer Networks project demonstrating:
ICMP, DNS resolution, TCP sockets, routing (TTL-based traceroute), network analysis.
