"""
app.py — Network Diagnostic Toolkit | Browser GUI
Minimalist, high-density, professional UI adhering to modern design taste.
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

# ── MINIMAL CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #111827;
    }
    code, pre, .stCodeBlock {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }
    
    #MainMenu, header, footer { visibility: hidden; }
    
    /* Clean button design */
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
        padding: 14px 16px;
        margin-bottom: 20px;
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
</style>
""", unsafe_allow_html=True)


# ── HELPERS ───────────────────────────────────────────────────────────────────
def status_indicator(status: str) -> str:
    s = (status or "").upper()
    if s in ("HEALTHY", "SUCCESS", "OPEN", "OK"):
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
<div style="padding-top: 0.5rem; padding-bottom: 1.5rem;">
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 20px;">⚡</span>
        <h1 style="font-size: 22px; font-weight: 700; margin: 0; color: #111827; letter-spacing: -0.02em;">Network Diagnostic Toolkit</h1>
    </div>
    <p style="font-size: 13px; color: #6B7280; margin-top: 4px; margin-bottom: 0;">
        Intelligent latency, routing, and DNS root-cause analysis.
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
            placeholder="google.com, 1.1.1.1, or 'Why is google.com slow?'",
            label_visibility="collapsed"
        )
    with col2:
        run = st.button("Run Check", type="primary", use_container_width=True)

with st.expander("Diagnostic Settings", expanded=False):
    c1, c2, c3 = st.columns(3)
    ping_count = c1.number_input("Ping Packets", min_value=1, max_value=20, value=4)
    ports_raw = c2.text_input("Port List", "22, 53, 80, 443, 8080")
    intent_opt = c3.selectbox("Intent Override", ["Auto", "slow", "full", "connectivity", "performance", "dns", "route", "access"])

# Quick target suggestions
st.markdown("<div style='font-size: 12px; color: #9CA3AF; margin-top: -8px; margin-bottom: 16px;'>Try: "
            "<a href='#' style='color:#4B5563; text-decoration:none; margin-right:10px;'>google.com</a>"
            "<a href='#' style='color:#4B5563; text-decoration:none; margin-right:10px;'>Why is google.com slow?</a>"
            "<a href='#' style='color:#4B5563; text-decoration:none; margin-right:10px;'>1.1.1.1</a>"
            "<a href='#' style='color:#4B5563; text-decoration:none;'>check port 443 on github.com</a>"
            "</div>", unsafe_allow_html=True)


# ── EXECUTION & DIAGNOSTICS ───────────────────────────────────────────────────
if run and query.strip():
    from analysis.diagnosis import parse_query
    parsed = parse_query(query.strip())

    # ── Handle Missing Target Gracefully ──────────────────────────────────────
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
        if qcol2.button("1.1.1.1 (Cloudflare)", use_container_width=True):
            set_target(f"{query.strip()} 1.1.1.1")
            st.rerun()
        if qcol3.button("github.com", use_container_width=True):
            set_target(f"{query.strip()} github.com")
            st.rerun()
        if qcol4.button("8.8.8.8 (Google DNS)", use_container_width=True):
            set_target(f"{query.strip()} 8.8.8.8")
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

    # Progress bar and status
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
                <span style="font-size:12px; color:#6B7280; font-weight:500;">QUERY</span>
                <div style="font-size:13px; font-weight:600; color:#111827;">"{query}"</div>
            </div>
            <div style="font-size:12px;">
                <span style="color:#6B7280;">Target:</span> <strong style="font-family:'JetBrains Mono',monospace;">{target}</strong> &nbsp;|&nbsp;
                <span style="color:#6B7280;">Intent:</span> <strong style="font-family:'JetBrains Mono',monospace;">{intent}</strong> &nbsp;|&nbsp;
                <span style="color:#6B7280;">Modules:</span> <span style="color:#4B5563;">{', '.join(sched)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── METRIC TILES ──────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Resolved Target", p.resolved_ip or target)
    m2.metric("Health Score", f"{processed.health_score} / 100")
    m3.metric("Overall Status", processed.overall_status)
    ping_res = p.results.get("ping", {})
    avg_lat = ping_res.get("avg_latency")
    m4.metric("Average RTT", f"{avg_lat:.1f} ms" if avg_lat is not None else "—")

    st.markdown("<hr style='margin: 18px 0; border: none; border-top: 1px solid #E5E7EB;'>", unsafe_allow_html=True)

    # ── SYNTHESIZED ROOT-CAUSE DIAGNOSIS ──────────────────────────────────────
    if processed.joint_root_cause:
        status_bg = "#ECFDF5" if processed.overall_status == "HEALTHY" else ("#FFFBEB" if processed.overall_status == "WARNING" else "#FEF2F2")
        status_border = "#10B981" if processed.overall_status == "HEALTHY" else ("#F59E0B" if processed.overall_status == "WARNING" else "#EF4444")
        st.markdown(f"""
        <div style="background:{status_bg}; border-left: 4px solid {status_border}; padding: 14px 16px; border-radius: 4px; margin-bottom: 20px;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #4B5563; letter-spacing: 0.05em; margin-bottom: 4px;">
                Synthesized Root-Cause Analysis
            </div>
            <div style="font-size: 14px; font-weight: 600; color: #111827;">
                {processed.joint_root_cause}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── DETECTED ISSUES & EXPLANATIONS ────────────────────────────────────────
    if processed.problems:
        st.markdown("<h3 style='font-size:14px; font-weight:600; margin-bottom:12px;'>Diagnostic Findings & Explanations</h3>", unsafe_allow_html=True)
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
                {f'<div style="font-size:12px; color:#6B7280; margin-top:6px; font-style:italic;">{prob.explanation}</div>' if prob.explanation else ''}
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── MODULE DETAILS ────────────────────────────────────────────────────────
    # 1. Connectivity (Ping)
    ping = p.results.get("ping")
    if ping:
        with st.container(border=True):
            st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:14px;'><strong style='font-size:14px;'>Connectivity (ICMP Ping)</strong> {status_indicator(ping.get('status'))}</div>", unsafe_allow_html=True)
            pc1, pc2 = st.columns([1, 2])
            with pc1:
                st.markdown(render_kv("Sent", ping.get('sent', 0)), unsafe_allow_html=True)
                st.markdown(render_kv("Received", ping.get('received', 0)), unsafe_allow_html=True)
                st.markdown(render_kv("Packet Loss", f"{ping.get('packet_loss', 0):.1f}%"), unsafe_allow_html=True)
                st.markdown(render_kv("Avg Latency", f"{ping.get('avg_latency', 0):.1f} ms"), unsafe_allow_html=True)
                st.markdown(render_kv("Min / Max", f"{ping.get('min_latency', 0):.1f} / {ping.get('max_latency', 0):.1f} ms"), unsafe_allow_html=True)
            with pc2:
                raw = ping.get("raw_times", [])
                if raw:
                    fig = go.Figure(go.Scatter(
                        y=raw, mode="lines+markers",
                        line=dict(color="#111827", width=1.5),
                        marker=dict(size=6, color="#111827")
                    ))
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=10, b=0),
                        height=130,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(visible=False),
                        yaxis=dict(
                            gridcolor="#F3F4F6",
                            title=dict(text="RTT (ms)", font=dict(size=11, color="#9CA3AF")),
                            tickfont=dict(size=10, color="#9CA3AF")
                        )
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # 2. Routing (Traceroute)
    tr = p.results.get("traceroute")
    if tr:
        with st.container(border=True):
            status = "SUCCESS" if tr.get("reached") else "WARNING"
            st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:14px;'><strong style='font-size:14px;'>Routing Path (Traceroute)</strong> {status_indicator(status)}</div>", unsafe_allow_html=True)
            hops = tr.get("hops", [])
            if hops:
                df = pd.DataFrame([{
                    "Hop": h["hop"],
                    "Router IP": h.get("ip") or "* * * (ICMP Rate Limited)",
                    "Hostname": h.get("hostname") or "-",
                    "RTT (ms)": h.get("latency_ms"),
                } for h in hops])
                st.dataframe(
                    df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Hop": st.column_config.NumberColumn(width="small"),
                        "RTT (ms)": st.column_config.NumberColumn(format="%.1f")
                    }
                )
            else:
                st.markdown("<span style='font-size:13px; color:#6B7280;'>No hops recorded (ICMP likely filtered).</span>", unsafe_allow_html=True)

    # 3. DNS & Ports
    dns = p.results.get("dns")
    port_d = p.results.get("port")
    if dns or port_d:
        colA, colB = st.columns(2)
        with colA:
            if dns:
                with st.container(border=True):
                    status = "SUCCESS" if dns.get("success") else "FAILED"
                    st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:14px;'><strong style='font-size:14px;'>DNS Resolution</strong> {status_indicator(status)}</div>", unsafe_allow_html=True)
                    st.markdown(render_kv("Domain", dns.get("domain", "")), unsafe_allow_html=True)
                    st.markdown(render_kv("Lookup Time", f"{dns.get('response_time_ms', 0):.1f} ms"), unsafe_allow_html=True)
                    ips = dns.get("ipv4_addresses", [])
                    if ips:
                        st.markdown("<div style='font-size:12px; color:#6B7280; margin-top:8px;'>IPv4 Records:</div>", unsafe_allow_html=True)
                        for ip in ips:
                            st.markdown(f"<div style='font-family:\"JetBrains Mono\",monospace; font-size:12px; color:#111827;'>• {ip}</div>", unsafe_allow_html=True)
        with colB:
            if port_d:
                with st.container(border=True):
                    st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:14px;'><strong style='font-size:14px;'>Port Accessibility</strong> <span style='font-size:12px; color:#6B7280;'>{port_d.get('open_count', 0)} open</span></div>", unsafe_allow_html=True)
                    ports_map = port_d.get("ports", {})
                    for p_num in sorted(ports_map.keys(), key=int):
                        info = ports_map[p_num]
                        is_open = info["status"] == "OPEN"
                        c_dot = "#10B981" if is_open else "#EF4444"
                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid #F3F4F6;">
                            <span style="font-family:'JetBrains Mono',monospace; font-size:12px;"><span style="color:{c_dot}; margin-right:6px;">●</span>{p_num}</span>
                            <span style="font-size:12px; color:#6B7280;">{info['service']} ({info['status']})</span>
                        </div>
                        """, unsafe_allow_html=True)

    # 4. Local Network Context
    net = p.results.get("network_info")
    if net:
        with st.expander("Local Network & Host Configuration"):
            n1, n2 = st.columns(2)
            with n1:
                st.markdown(render_kv("Hostname", net.get("hostname", "-")), unsafe_allow_html=True)
                st.markdown(render_kv("Local IP", net.get("local_ip", "-")), unsafe_allow_html=True)
                st.markdown(render_kv("Subnet Mask", net.get("subnet_mask", "-")), unsafe_allow_html=True)
            with n2:
                st.markdown(render_kv("Default Gateway", net.get("default_gateway", "-")), unsafe_allow_html=True)
                st.markdown(render_kv("DNS Servers", ", ".join(net.get("dns_servers", []) or ["-"])), unsafe_allow_html=True)

    # ── ACTIONABLE RECOMMENDATIONS ────────────────────────────────────────────
    if processed.recommendations:
        with st.container(border=True):
            st.markdown("<strong style='font-size:14px;'>Recommended Actions</strong>", unsafe_allow_html=True)
            for rec in processed.recommendations:
                st.markdown(f"<div style='font-size:13px; color:#374151; margin-top:6px;'>→ {rec}</div>", unsafe_allow_html=True)

    # ── EXPORT OPTIONS ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Export Diagnostic Reports"):
        from reports.report_generator import generate_txt_report, generate_json_report
        t1, t2 = st.columns(2)
        t1.download_button("Download Report (.txt)", generate_txt_report(processed), file_name=f"report_{target}.txt", use_container_width=True)
        t2.download_button("Download Data (.json)", generate_json_report(processed), file_name=f"data_{target}.json", use_container_width=True)
        st.json(p.results)

    st.markdown(f"<div style='text-align:right; font-size:11px; color:#9CA3AF; margin-top:16px;'>Diagnostic Suite executed in {p.total_time_ms:.0f} ms</div>", unsafe_allow_html=True)

elif run:
    st.info("Please enter a valid target or query to begin.")
