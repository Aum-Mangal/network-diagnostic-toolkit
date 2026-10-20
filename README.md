# Network Diagnostic Toolkit

> An intelligent, full-stack Python network diagnostic suite featuring natural language intent detection, cross-protocol diagnostics (Ping, DNS, Traceroute, Port Scan, Local LAN info), an explainable rules engine, automated test suite, and a sleek modern browser interface.

---

## Key Features

- **Phase 2 — Input Validation & Resolution**: Validates IPv4, IPv6, localhost, and fully qualified domain names with DNS forward and reverse lookups.
- **Phase 3 — ICMP Ping Engine**: Measures latency statistics (min, avg, max, RTT variance) and packet loss percentage.
- **Phase 4 — DNS Resolver**: Collects A (IPv4) and AAAA (IPv6) records and measures DNS query response time.
- **Phase 5 — Traceroute & Path Analysis**: Probes intermediate hops and hop-by-hop latency. Distinguishes standard router ICMP rate limiting (RFC 1812) from true path bottlenecks.
- **Phase 6 — Concurrent TCP Port Scanner**: High-speed socket checks across standard service ports (HTTP, HTTPS, SSH, DNS, etc.) or custom port ranges.
- **Phase 7 — Local Network Context**: Inspects local IP, subnet mask, default gateway, and local DNS servers.
- **Phase 8 & 9 — Explainable Diagnostic Rules Engine**:
  - Calculates a 0–100 overall Network Health Score.
  - Every detected issue includes **Measured Value**, **Threshold**, and **Technical Explanation**.
  - Synthesizes a unified root-cause diagnosis.
- **Phase 10 & 11 — Modern Interfaces**:
  - Terminal dashboard with rich ASCII tables and metric bars.
  - Minimalist, high-density Streamlit web interface (`app.py`).
- **Phase 12 & 13 — Natural Language & Smart Planner**:
  - Translates queries like *"Why is google.com slow?"* into targeted diagnostic pipelines (DNS → Ping → Traceroute → Joint Analysis).
  - Handles missing targets gracefully with clarification prompts.
- **Phase 14 — Export**: Saves comprehensive plain-text (`.txt`) and machine-readable (`.json`) reports.
- **Automated Verification**: Full `pytest` test suite covering validation, NL parsing, scoring, and report exports.

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Browser GUI
```bash
streamlit run app.py
```

### 3. Run the CLI
```bash
# Direct target
python main.py google.com

# Natural language query
python main.py "Why is google.com slow?"

# Custom ports and export reports
python main.py google.com --ports 22 80 443 --save txt json

# Generate matplotlib charts
python main.py google.com --graphs
```

### 4. Run Automated Tests
```bash
pytest tests
```

---

## Architecture & Project Structure

```
network-diagnostic-toolkit/
├── main.py                  # CLI entry point with query interpreter
├── app.py                   # Modern browser GUI (Streamlit + Plotly)
├── requirements.txt         # Project dependencies
├── core/
│   ├── validator.py         # Input validation & DNS resolution
│   ├── diagnostic_engine.py # Smart module orchestrator
│   └── result_processor.py  # Diagnostic rules engine & health scoring
├── modules/
│   ├── ping.py              # ICMP ping implementation
│   ├── traceroute.py        # Traceroute & hop delay measurement
│   ├── dns_lookup.py        # DNS A/AAAA query module
│   ├── port_scanner.py      # Multi-threaded TCP port scanner
│   └── network_info.py      # Host & gateway configuration
├── analysis/
│   ├── latency.py           # Latency metrics & statistics
│   ├── packet_loss.py       # Loss calculation & degradation rules
│   └── diagnosis.py         # NL query parser & intent classifier
├── ui/
│   └── dashboard.py         # Rich terminal UI & matplotlib charts
├── reports/
│   └── report_generator.py  # Formatted TXT & structured JSON reports
└── tests/
    ├── test_validator.py        # Input validation test cases
    ├── test_diagnosis_nl.py     # NL query & target extraction tests
    ├── test_result_processor.py # Rules engine & scoring tests
    └── test_report_generator.py # Report generation tests
```

---

## Tech Stack

- **Python 3.10+**
- **Streamlit & Plotly** — High-taste, responsive web application
- **Rich** — Styled terminal UI, panels, and progress bars
- **dnspython** — Low-level DNS resolution
- **pytest** — Unit and integration test suite
