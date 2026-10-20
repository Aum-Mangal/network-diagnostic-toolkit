"""
app.py — Network Diagnostic Toolkit | Browser GUI
Advanced Computer Networks Diagnostic Suite:
- OSI 4-Layer Protocol Health Matrix
- LAN vs. WAN Comparative Benchmark (Wi-Fi/Gateway vs. Remote Target)
- Interactive Hop-by-Hop Visual Network Route (Topology Path)
- TCP SYN Fallback for ICMP-filtered enterprise hosts (Amazon, Microsoft, Cloudflare)
- RFC 1812 Router Rate-Limiting Detection
"""

import json
import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Network Diagnostic Toolkit",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── PROFESSIONAL MINIMAL CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #111827;
    }
    code, pre, .stCodeBlock {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }
    
    #MainMenu, header, footer { visibility: hidden; }
    
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        border: 1px solid #E5E7EB;
        background: #FFFFFF;
        color: #111827;
        transition: all 0.15s ease;
        padding: 0.45rem 1rem;
    }
    .stButton > button:hover {
        border-color: #111827;
        color: #111827;
        background: #F9FAFB;
    }
    
    .stButton > button[kind="primary"] {
        background: #111827;
        color: #FFFFFF;
        border: 1px solid #111827;
    }
    .stButton > button[kind="primary"]:hover {
        background: #1F2937;
        border-color: #1F2937;
        color: #FFFFFF;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #E5E7EB;
        border-radius: 6px;
    }

    /* Status indicators */
    .dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }
    .dot-healthy { background-color: #10B981; }
    .dot-warning { background-color: #F59E0B; }
    .dot-critical { background-color: #EF4444; }
    .dot-neutral { background-color: #6B7280; }
    
    .status-text {
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    
    .card-banner {
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 16px;
        border: 1px solid #E5E7EB;
        background: #F9FAFB;
    }

    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .badge-critical { background: #FEE2E2; color: #991B1B; }
    .badge-warning { background: #FEF3C7; color: #92400E; }
    .badge-info { background: #E0E7FF; color: #3730A3; }

    /* Visual Hop Route Map */
    .hop-node {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        border-left: 2px solid #E5E7EB;
        margin-left: 14px;
        position: relative;
    }
    .hop-node::before {
        content: "";
        position: absolute;
        left: -6px;
        top: 14px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #111827;
    }
    .hop-node.rate-limited::before {
        background: #9CA3AF;
    }
    .hop-node.spike::before {
        background: #F59E0B;
    }
    .hop-node.destination::before {
        background: #10B981;
    }
</style>
""", unsafe_allow_html=True)


# ── HELPERS ───────────────────────────────────────────────────────────────────
def status_indicator(status: str) -> str:
    s = (status or "").upper()
    if s in ("HEALTHY", "SUCCESS", "OPEN", "OK", "ICMP_BLOCKED_TCP_OK"):
        return '<span class="dot dot-healthy"></span><span class="status-text" style="color:#047857;">HEALTHY</span>'
    if s in ("DEGRADED", "WARNING"):
        return '<span class="dot dot-warning"></span><span class="status-text" style="color:#B45309;">WARNING</span>'
    if s in ("CRITICAL", "FAILED", "CLOSED", "UNREACHABLE"):
        return '<span class="dot dot-critical"></span><span class="status-text" style="color:#B91C1C;">CRITICAL</span>'
    return f'<span class="dot dot-neutral"></span><span class="status-text" style="color:#4B5563;">{s}</span>'


def render_kv(key: str, val: str):
    return f"""
    <div style="display:flex; justify-content:space-between; padding: 6px 0; border-bottom: 1px solid #F3F4F6; font-size: 13px;">
        <span style="color: #6B7280">{key}</span>
        <span style="font-family: 'JetBrains Mono', monospace; color: #111827; font-weight: 500;">{val}</span>
    </div>
    """


# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding-top: 0.5rem; padding-bottom: 1.2rem;">
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 20px;">⚡</span>
        <h1 style="font-size: 22px; font-weight: 700; margin: 0; color: #111827; letter-spacing: -0.02em;">Network Diagnostic Toolkit</h1>
    </div>
    <p style="font-size: 13px; color: #6B7280; margin-top: 4px; margin-bottom: 0;">
        Full-stack OSI layer diagnostics, root-cause synthesis, and hop-by-hop route visualization.
    </p>
</div>
""", unsafe_allow_html=True)

# ── SESSION STATE FOR QUICK TARGET CLICKS ──────────────────────────────────────
if "query_input" not in st.session_state:
    st.session_state.query_input = ""


def set_target(t: str):
    st.session_state.query_input = t


# ── INPUT SECTION ─────────────────────────────────────────────────────────────
with st.container(border=True):
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input(
            "Target or Query",
            value=st.session_state.query_input,
            placeholder="google.com, amazon.com, 1.1.1.1, or 'Why is github.com slow?'",
            label_visibility="collapsed"
        )
    with col2:
        run = st.button("Run Check", type="primary", use_container_width=True)

with st.expander("Diagnostic Configuration", expanded=False):
    c1, c2, c3 = st.columns(3)
    ping_count = c1.number_input("Ping Packets", min_value=1, max_value=20, value=4)
    ports_raw = c2.text_input("Port List", "22, 53, 80, 443, 8080")
    intent_opt = c3.selectbox("Intent Override", ["Auto", "slow", "full", "connectivity", "performance", "dns", "route", "access"])

# Quick target suggestion pills
st.markdown("""
<div style='font-size: 12px; color: #9CA3AF; margin-top: -6px; margin-bottom: 18px;'>
    <span style="color:#6B7280; font-weight:500;">Quick Test:</span>
    <span style="color:#111827; margin-left:6px; font-family:'JetBrains Mono',monospace;">google.com</span> (Standard ICMP) &nbsp;|&nbsp;
    <span style="color:#111827; font-family:'JetBrains Mono',monospace;">amazon.com</span> (ICMP Filtered + TCP) &nbsp;|&nbsp;
    <span style="color:#111827; font-family:'JetBrains Mono',monospace;">1.1.1.1</span> (Cloudflare Anycast)
</div>
""", unsafe_allow_html=True)


# ── EXECUTION & DIAGNOSTICS ───────────────────────────────────────────────────
if run and query.strip():
    from analysis.diagnosis import parse_query
    parsed = parse_query(query.strip())

    # Handle Missing Target Gracefully
    if parsed.needs_target or not parsed.target:
        st.markdown(f"""
        <div class="card-banner" style="border-left: 3px solid #F59E0B;">
            <div style="font-weight: 600; color: #92400E; font-size: 14px; margin-bottom: 4px;">⚠️ Target Destination Required</div>
            <div style="color: #78350F; font-size: 13px;">{parsed.clarification_prompt}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<p style='font-size:13px; font-weight:500; color:#4B5563; margin-bottom:6px;'>Select a destination to diagnose with this intent:</p>", unsafe_allow_html=True)
        qcol1, qcol2, qcol3, qcol4 = st.columns(4)
        if qcol1.button("google.com", use_container_width=True):
            set_target(f"{query.strip()} google.com")
            st.rerun()
        if qcol2.button("amazon.com", use_container_width=True):
            set_target(f"{query.strip()} amazon.com")
            st.rerun()
        if qcol3.button("1.1.1.1", use_container_width=True):
            set_target(f"{query.strip()} 1.1.1.1")
            st.rerun()
        if qcol4.button("github.com", use_container_width=True):
            set_target(f"{query.strip()} github.com")
            st.rerun()
        st.stop()

    target = parsed.target
    intent = intent_opt.lower() if intent_opt != "Auto" else parsed.intent

    # Ports
    if parsed.custom_ports:
        ports = parsed.custom_ports
    else:
        try:
            ports = [int(p.strip()) for p in ports_raw.split(",") if p.strip()]
        except Exception:
            ports = [22, 53, 80, 443, 8080]

    prog_bar = st.progress(0)
    status_txt = st.empty()

    def upd(msg, pct):
        status_txt.markdown(f"<span style='font-size:13px; color:#6B7280;'>{msg}</span>", unsafe_allow_html=True)
        prog_bar.progress(pct)

    upd(f"Resolving & validating target '{target}'...", 15)
    from core.validator import validate
    val = validate(target)

    if not val.is_valid:
        prog_bar.empty()
        status_txt.empty()
        st.error(val.error)
        st.stop()

    upd(f"Running diagnostic engine (Intent: {intent})...", 45)
    from core.diagnostic_engine import DiagnosticEngine
    engine = DiagnosticEngine(val)
    payload = engine.run(intent=intent, custom_ports=ports, ping_count=ping_count)

    upd("Applying diagnostic rules & synthesizing root causes...", 85)
    from core.result_processor import ResultProcessor
    processed = ResultProcessor().process(payload)

    upd("Complete.", 100)
    time.sleep(0.15)
    prog_bar.empty()
    status_txt.empty()

    p = payload

    # ── QUERY INTERPRETATION BANNER ───────────────────────────────────────────
    if parsed.natural_language:
        from core.diagnostic_engine import INTENT_MODULE_MAP
        sched = INTENT_MODULE_MAP.get(intent, ["full"])
        st.markdown(f"""
        <div class="card-banner" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
                <span style="font-size:11px; color:#6B7280; font-weight:600; text-transform:uppercase;">NATURAL QUERY</span>
                <div style="font-size:13px; font-weight:600; color:#111827;">"{query}"</div>
            </div>
            <div style="font-size:12px;">
                <span style="color:#6B7280;">Target:</span> <strong style="font-family:'JetBrains Mono',monospace;">{target}</strong> &nbsp;|&nbsp;
                <span style="color:#6B7280;">Intent:</span> <strong style="font-family:'JetBrains Mono',monospace;">{intent}</strong> &nbsp;|&nbsp;
                <span style="color:#6B7280;">Pipeline:</span> <span style="color:#4B5563;">{', '.join(sched)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── EXECUTIVE SUMMARY & SCORE ─────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Destination IP", p.resolved_ip or target)
    m2.metric("Health Score", f"{processed.health_score} / 100")
    m3.metric("Network Status", processed.overall_status)
    ping_res = p.results.get("ping", {})
    avg_lat = ping_res.get("avg_latency")
    m4.metric("Avg Latency (RTT)", f"{avg_lat:.1f} ms" if avg_lat is not None else "—")

    # Synthesized Root-Cause Callout
    if processed.joint_root_cause:
        status_bg = "#ECFDF5" if processed.overall_status == "HEALTHY" else ("#FFFBEB" if processed.overall_status == "WARNING" else "#FEF2F2")
        status_border = "#10B981" if processed.overall_status == "HEALTHY" else ("#F59E0B" if processed.overall_status == "WARNING" else "#EF4444")
        st.markdown(f"""
        <div style="background:{status_bg}; border-left: 4px solid {status_border}; padding: 14px 16px; border-radius: 4px; margin-top: 14px; margin-bottom: 20px;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #4B5563; letter-spacing: 0.05em; margin-bottom: 4px;">
                Synthesized Root-Cause Verdict
            </div>
            <div style="font-size: 13.5px; font-weight: 600; color: #111827; line-height: 1.5;">
                {processed.joint_root_cause}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── LAN VS WAN BENCHMARK ──────────────────────────────────────────────────
    # Isolates local Wi-Fi / Router issues from Internet WAN delays
    net_info = p.results.get("network_info")
    gw_latency = net_info.get("gateway_latency_ms") if net_info else None
    gw_ip = net_info.get("default_gateway") if net_info else None

    if gw_latency is not None and avg_lat is not None:
        with st.container(border=True):
            st.markdown("<strong style='font-size:13.5px;'>Local LAN vs. Remote WAN Benchmark</strong>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:12px; color:#6B7280; margin-bottom:12px;'>Isolates whether network delay originates inside your home/Wi-Fi or on the Internet.</p>", unsafe_allow_html=True)
            
            b1, b2 = st.columns(2)
            with b1:
                st.markdown(f"""
                <div style="padding:10px 14px; border-radius:6px; background:#F9FAFB; border:1px solid #E5E7EB;">
                    <div style="font-size:11px; color:#6B7280; text-transform:uppercase; font-weight:600;">1. Local Wi-Fi / Router (LAN)</div>
                    <div style="font-size:20px; font-weight:700; color:#111827; margin:4px 0;">{gw_latency:.1f} ms</div>
                    <div style="font-size:12px; color:#047857;">● Gateway: {gw_ip or 'Local Router'}</div>
                </div>
                """, unsafe_allow_html=True)
            with b2:
                st.markdown(f"""
                <div style="padding:10px 14px; border-radius:6px; background:#F9FAFB; border:1px solid #E5E7EB;">
                    <div style="font-size:11px; color:#6B7280; text-transform:uppercase; font-weight:600;">2. Destination Cloud (WAN)</div>
                    <div style="font-size:20px; font-weight:700; color:#111827; margin:4px 0;">{avg_lat:.1f} ms</div>
                    <div style="font-size:12px; color:#4B5563;">● Target: {target}</div>
                </div>
                """, unsafe_allow_html=True)

            # Plain-language explanation
            if gw_latency <= 5.0:
                st.markdown(f"<div style='font-size:12px; color:#047857; margin-top:8px;'>✓ <strong>Local Wi-Fi is optimal ({gw_latency:.1f}ms).</strong> Any observed latency is introduced upstream in your ISP or the destination network.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='font-size:12px; color:#B45309; margin-top:8px;'>⚠️ <strong>Local Wi-Fi / Router latency is elevated ({gw_latency:.1f}ms).</strong> Wi-Fi congestion or router bufferbloat is contributing to delays.</div>", unsafe_allow_html=True)

    # ── OSI 4-LAYER PROTOCOL HEALTH MATRIX ────────────────────────────────────
    st.markdown("<h3 style='font-size:14px; font-weight:600; margin-top:20px; margin-bottom:10px;'>OSI 4-Layer Protocol Health Matrix</h3>", unsafe_allow_html=True)
    
    dns_res = p.results.get("dns", {})
    port_res = p.results.get("port", {})
    
    osi_data = [
        {
            "OSI Layer": "Layer 7 — Application",
            "Protocol": "DNS (Domain Name Resolution)",
            "Status": "HEALTHY" if dns_res.get("success") else ("SKIPPED" if "dns" not in p.results else "FAILED"),
            "Key Measurement": f"{dns_res.get('response_time_ms', 0):.1f} ms lookup time ({len(dns_res.get('ipv4_addresses', []))} A records)" if dns_res.get("success") else ("Not evaluated" if "dns" not in p.results else dns_res.get("error", "Failed")),
        },
        {
            "OSI Layer": "Layer 4 — Transport",
            "Protocol": "TCP (SYN Handshake & Ports)",
            "Status": "HEALTHY" if (port_res.get("open_count", 0) > 0 or ping_res.get("tcp_fallback")) else ("SKIPPED" if "port" not in p.results else "WARNING"),
            "Key Measurement": f"{port_res.get('open_count', 0)} open service ports" if port_res else (f"TCP SYN RTT {ping_res['tcp_fallback']['rtt_ms']:.1f}ms" if ping_res.get("tcp_fallback") else "Transport healthy"),
        },
        {
            "OSI Layer": "Layer 3 — Network",
            "Protocol": "ICMP & IP Routing (TTL)",
            "Status": "HEALTHY" if ping_res.get("status") in ("HEALTHY", "ICMP_BLOCKED_TCP_OK") else ping_res.get("status", "SKIPPED"),
            "Key Measurement": f"ICMP Filtered (Host alive via TCP)" if ping_res.get("icmp_blocked") else f"{ping_res.get('avg_latency', 0):.1f}ms RTT ({ping_res.get('packet_loss', 0):.1f}% loss)",
        },
        {
            "OSI Layer": "Layer 2 / 1 — Data Link & LAN",
            "Protocol": "Ethernet / 802.11 Wi-Fi",
            "Status": "HEALTHY" if net_info and net_info.get("default_gateway") else "UNKNOWN",
            "Key Measurement": f"Gateway {net_info.get('default_gateway', 'None')} (Subnet: {net_info.get('subnet_mask', '-')})" if net_info else "Local interface active",
        }
    ]
    st.dataframe(pd.DataFrame(osi_data), hide_index=True, use_container_width=True)

    # ── DETECTED ISSUES & EXPLANATIONS ────────────────────────────────────────
    if processed.problems:
        st.markdown("<h3 style='font-size:14px; font-weight:600; margin-top:20px; margin-bottom:12px;'>Diagnostic Findings & Explanations</h3>", unsafe_allow_html=True)
        for prob in processed.problems:
            sev_class = f"badge-{prob.severity.lower()}"
            st.markdown(f"""
            <div style="border: 1px solid #E5E7EB; border-radius: 6px; padding: 12px 14px; margin-bottom: 10px; background: #FFFFFF;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                    <span style="font-size:13px; font-weight:600; color:#111827;">{prob.description}</span>
                    <span class="badge {sev_class}">{prob.severity}</span>
                </div>
                <div style="font-size:13px; color:#4B5563; margin-bottom: 6px;">{prob.detail}</div>
                <div style="display:flex; gap:16px; font-size:11px; color:#6B7280; font-family:'JetBrains Mono',monospace; background:#F9FAFB; padding:6px 10px; border-radius:4px;">
                    <span><strong>Measured:</strong> {prob.measurement or 'N/A'}</span>
                    <span><strong>Threshold:</strong> {prob.threshold or 'N/A'}</span>
                </div>
                {f'<div style="font-size:12px; color:#4B5563; margin-top:6px; font-style:italic;">{prob.explanation}</div>' if prob.explanation else ''}
            </div>
            """, unsafe_allow_html=True)

    # ── VISUAL NETWORK ROUTE TOPOLOGY MAP (Phase 5) ───────────────────────────
    tr = p.results.get("traceroute")
    if tr:
        with st.container(border=True):
            status = "SUCCESS" if tr.get("reached") else "WARNING"
            st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:14px;'><strong style='font-size:14px;'>Hop-by-Hop Visual Network Route</strong> {status_indicator(status)}</div>", unsafe_allow_html=True)
            hops = tr.get("hops", [])
            
            if hops:
                st.markdown("<div style='font-size:12px; color:#6B7280; margin-bottom:14px;'>Interactive path tracing TTL increments from your device to the destination server:</div>", unsafe_allow_html=True)
                
                # Starting Node: User's PC
                st.markdown("""
                <div class="hop-node">
                    <div style="font-weight:600; font-size:13px; color:#111827;">Your PC</div>
                    <div style="font-family:'JetBrains Mono',monospace; font-size:11.5px; color:#6B7280;">Local Client</div>
                    <span style="margin-left:auto; font-size:11px; color:#047857; font-weight:600;">0.0 ms</span>
                </div>
                """, unsafe_allow_html=True)

                for h in hops:
                    h_num = h["hop"]
                    ip = h.get("ip")
                    hn = h.get("hostname")
                    lat = h.get("latency_ms")

                    is_rate_limited = lat is None or ip is None
                    is_destination = h_num == len(hops) and tr.get("reached")
                    node_class = "destination" if is_destination else ("rate-limited" if is_rate_limited else "")

                    ip_display = ip or "* * * (ICMP Rate Limited)"
                    hn_display = f" — {hn[:35]}" if hn and hn != ip else ""
                    
                    if is_rate_limited:
                        lat_display = '<span style="color:#9CA3AF; font-size:11px;">* (RFC 1812)</span>'
                    elif lat < 30:
                        lat_display = f'<span style="color:#047857; font-weight:600; font-size:11.5px;">{lat:.1f} ms</span>'
                    elif lat < 100:
                        lat_display = f'<span style="color:#B45309; font-weight:600; font-size:11.5px;">{lat:.1f} ms</span>'
                    else:
                        lat_display = f'<span style="color:#B91C1C; font-weight:600; font-size:11.5px;">{lat:.1f} ms (Spike)</span>'

                    st.markdown(f"""
                    <div class="hop-node {node_class}">
                        <div style="font-size:12.5px; color:#111827; font-weight:500;">Hop {h_num}</div>
                        <div style="font-family:'JetBrains Mono',monospace; font-size:11.5px; color:#4B5563;">{ip_display}{hn_display}</div>
                        <span style="margin-left:auto; font-family:'JetBrains Mono',monospace;">{lat_display}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("<span style='font-size:13px; color:#6B7280;'>No hops recorded (ICMP likely filtered).</span>", unsafe_allow_html=True)

    # ── PROTOCOL DETAILS (PING, DNS, PORTS) ───────────────────────────────────
    col_p, col_d = st.columns(2)
    
    with col_p:
        ping = p.results.get("ping")
        if ping:
            with st.container(border=True):
                st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:12px;'><strong style='font-size:14px;'>Connectivity (ICMP & TCP)</strong> {status_indicator(ping.get('status'))}</div>", unsafe_allow_html=True)
                st.markdown(render_kv("Packets Sent/Recv", f"{ping.get('sent',0)} / {ping.get('received',0)}"), unsafe_allow_html=True)
                st.markdown(render_kv("Packet Loss", f"{ping.get('packet_loss',0):.1f}%"), unsafe_allow_html=True)
                st.markdown(render_kv("Avg RTT", f"{ping.get('avg_latency',0):.1f} ms"), unsafe_allow_html=True)
                st.markdown(render_kv("Jitter (Delay Var.)", f"{ping.get('jitter_ms',0):.1f} ms"), unsafe_allow_html=True)

                if ping.get("icmp_blocked"):
                    tcp_f = ping.get("tcp_fallback", {})
                    st.markdown(f"<div style='background:#F0FDF4; border:1px solid #DCFCE7; padding:8px 10px; border-radius:4px; font-size:11.5px; color:#166534; margin-top:8px;'>✓ ICMP Echo blocked; Verified alive via TCP port {tcp_f.get('port', 443)} ({tcp_f.get('rtt_ms', 0):.1f}ms).</div>", unsafe_allow_html=True)

                raw = ping.get("raw_times", [])
                if raw and len(raw) > 1:
                    fig = go.Figure(go.Scatter(
                        y=raw, mode="lines+markers",
                        line=dict(color="#111827", width=1.5),
                        marker=dict(size=6, color="#111827")
                    ))
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=10, b=0),
                        height=100,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(visible=False),
                        yaxis=dict(
                            gridcolor="#F3F4F6",
                            title=dict(text="RTT (ms)", font=dict(size=10, color="#9CA3AF")),
                            tickfont=dict(size=9, color="#9CA3AF")
                        )
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with col_d:
        dns = p.results.get("dns")
        if dns:
            with st.container(border=True):
                st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:12px;'><strong style='font-size:14px;'>DNS Resolution (L7)</strong> {status_indicator('SUCCESS' if dns.get('success') else 'FAILED')}</div>", unsafe_allow_html=True)
                st.markdown(render_kv("Domain", dns.get("domain", "")), unsafe_allow_html=True)
                st.markdown(render_kv("Lookup Latency", f"{dns.get('response_time_ms', 0):.1f} ms"), unsafe_allow_html=True)
                ips = dns.get("ipv4_addresses", [])
                if ips:
                    st.markdown("<div style='font-size:12px; color:#6B7280; margin-top:8px;'>A (IPv4) Records:</div>", unsafe_allow_html=True)
                    for ip in ips[:3]:
                        st.markdown(f"<div style='font-family:\"JetBrains Mono\",monospace; font-size:11.5px; color:#111827;'>• {ip}</div>", unsafe_allow_html=True)

    # ── ACTIONABLE RECOMMENDATIONS ────────────────────────────────────────────
    if processed.recommendations:
        with st.container(border=True):
            st.markdown("<strong style='font-size:13.5px;'>Recommended Technical Actions</strong>", unsafe_allow_html=True)
            for rec in processed.recommendations:
                st.markdown(f"<div style='font-size:13px; color:#374151; margin-top:5px;'>→ {rec}</div>", unsafe_allow_html=True)

    # ── EXPORT OPTIONS ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Export Diagnostic Reports"):
        from reports.report_generator import generate_txt_report, generate_json_report
        t1, t2 = st.columns(2)
        t1.download_button("Download Report (.txt)", generate_txt_report(processed), file_name=f"report_{target}.txt", use_container_width=True)
        t2.download_button("Download Data (.json)", generate_json_report(processed), file_name=f"data_{target}.json", use_container_width=True)
        st.json(p.results)

    st.markdown(f"<div style='text-align:right; font-size:11px; color:#9CA3AF; margin-top:14px;'>Diagnostic Suite executed in {p.total_time_ms:.0f} ms</div>", unsafe_allow_html=True)

elif run:
    st.info("Please enter a valid target or query to begin.")
