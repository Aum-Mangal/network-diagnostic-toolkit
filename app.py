"""
app.py — Network Diagnostic Toolkit | Browser GUI
Minimalist, high-density, professional UI.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json
import time

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Network Diagnostic",
    page_icon="▤",
    layout="centered", # Centered layout prevents excessive white space on large monitors
    initial_sidebar_state="collapsed",
)

# ── MINIMAL CSS ───────────────────────────────────────────────────────────────
# We strip out the heavy "AI" shadows/gradients and use a raw, clean, 
# Vercel/Linear inspired aesthetic via native Streamlit containers.
st.markdown("""
<style>
    /* Typography refinements */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    code, pre, .stCodeBlock {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }
    
    /* Clean up default Streamlit elements */
    #MainMenu, header, footer { visibility: hidden; }
    
    /* Sleek buttons */
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        border: 1px solid #E5E7EB;
        background: #FFFFFF;
        color: #111827;
        transition: all 0.1s ease;
    }
    .stButton > button:hover {
        border-color: #111827;
        color: #111827;
    }
    
    /* Primary button override (the search button) */
    .stButton > button[kind="primary"] {
        background: #111827;
        color: #FFFFFF;
        border: 1px solid #111827;
    }
    .stButton > button[kind="primary"]:hover {
        background: #374151;
        border-color: #374151;
        color: #FFFFFF;
    }

    /* Subdued expanders */
    .streamlit-expanderHeader {
        font-weight: 500;
        color: #4B5563;
    }
    
    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid #E5E7EB;
        border-radius: 6px;
    }

    /* Status Dots */
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
        font-size: 13px;
        font-weight: 500;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        color: #4B5563;
    }
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def status_indicator(status: str) -> str:
    s = (status or "").upper()
    if s in ("HEALTHY", "SUCCESS", "OPEN", "OK"):
        return '<span class="dot dot-healthy"></span><span class="status-text">HEALTHY</span>'
    if s in ("DEGRADED", "WARNING"):
        return '<span class="dot dot-warning"></span><span class="status-text">DEGRADED</span>'
    if s in ("CRITICAL", "FAILED", "CLOSED", "UNREACHABLE"):
        return '<span class="dot dot-critical"></span><span class="status-text">CRITICAL</span>'
    return f'<span class="dot dot-neutral"></span><span class="status-text">{s}</span>'

def render_kv(key: str, val: str):
    return f"""
    <div style="display:flex; justify-content:space-between; padding: 4px 0; border-bottom: 1px solid #F3F4F6; font-size: 13px;">
        <span style="color: #6B7280">{key}</span>
        <span style="font-family: 'JetBrains Mono', monospace; color: #111827; font-weight: 500;">{val}</span>
    </div>
    """

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding-top: 1rem; padding-bottom: 2rem;">
    <h1 style="font-size: 24px; font-weight: 600; margin: 0; color: #111827; letter-spacing: -0.02em;">Network Diagnostic</h1>
    <p style="font-size: 14px; color: #6B7280; margin-top: 4px;">Run latency, routing, and DNS checks.</p>
</div>
""", unsafe_allow_html=True)

# ── INPUT SECTION ─────────────────────────────────────────────────────────────
with st.container(border=True):
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input(
            "Target", 
            placeholder="google.com, 1.1.1.1, or 'why is github slow?'",
            label_visibility="collapsed"
        )
    with col2:
        run = st.button("Run Diagnostic", type="primary", use_container_width=True)

with st.expander("Configuration", expanded=False):
    c1, c2, c3 = st.columns(3)
    ping_count = c1.number_input("Ping Count", min_value=1, max_value=20, value=4)
    ports_raw = c2.text_input("Ports", "22, 53, 80, 443, 8080")
    intent_opt = c3.selectbox("Intent", ["Auto", "full", "connectivity", "performance", "dns", "route"])

# ── EXECUTION ─────────────────────────────────────────────────────────────────
if run and query.strip():
    try:
        ports = [int(p.strip()) for p in ports_raw.split(",") if p.strip()]
    except:
        ports = [22, 53, 80, 443, 8080]

    prog_bar = st.progress(0)
    status_txt = st.empty()

    def upd(msg, pct):
        status_txt.markdown(f"<span style='font-size:13px; color:#6B7280;'>{msg}</span>", unsafe_allow_html=True)
        prog_bar.progress(pct)

    upd("Parsing query...", 10)
    from analysis.diagnosis import parse_query
    parsed = parse_query(query.strip())
    target = parsed.target or query.strip()
    intent = intent_opt.lower() if intent_opt != "Auto" else parsed.intent

    upd(f"Validating {target}...", 20)
    from core.validator import validate
    val = validate(target)

    if not val.is_valid:
        prog_bar.empty(); status_txt.empty()
        st.error(val.error)
        st.stop()

    upd("Running diagnostic engine...", 40)
    from core.diagnostic_engine import DiagnosticEngine
    engine = DiagnosticEngine(val)
    payload = engine.run(intent=intent, custom_ports=ports, ping_count=ping_count)

    upd("Processing results...", 90)
    from core.result_processor import ResultProcessor
    processed = ResultProcessor().process(payload)

    upd("Complete.", 100)
    time.sleep(0.2)
    prog_bar.empty(); status_txt.empty()

    p = payload

    # ── REPORT VIEW ───────────────────────────────────────────────────────────
    if parsed.natural_language:
        st.markdown(f"<div style='background:#F3F4F6; padding: 12px; border-radius: 6px; font-size:13px; margin-bottom:20px;'><span style='color:#4B5563'>Query:</span> <strong>{query}</strong> &nbsp;→&nbsp; Target: <code>{target}</code> | Intent: <code>{intent}</code></div>", unsafe_allow_html=True)

    # Top metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Resolved IP", p.resolved_ip or "—")
    c2.metric("Health Score", f"{processed.health_score}/100")
    
    score = processed.health_score
    if score >= 85:
        c3.metric("Status", "HEALTHY")
    elif score >= 60:
        c3.metric("Status", "WARNING")
    else:
        c3.metric("Status", "CRITICAL")
        
    c4.metric("Latency (avg)", f"{p.results.get('ping', {}).get('avg_latency', '—')} ms")

    st.markdown("<hr style='margin: 24px 0; border: none; border-top: 1px solid #E5E7EB;'>", unsafe_allow_html=True)

    # Diagnosed Problems (Rules Engine)
    if processed.problems:
        st.markdown("<h3 style='font-size:14px; font-weight:600; margin-bottom:12px;'>Detected Issues</h3>", unsafe_allow_html=True)
        for prob in processed.problems:
            color = "#EF4444" if prob.severity == "critical" else "#F59E0B"
            st.markdown(f"""
            <div style="border-left: 3px solid {color}; padding-left: 12px; margin-bottom: 12px;">
                <div style="font-size:13px; font-weight:600; color:#111827;">{prob.description}</div>
                <div style="font-size:13px; color:#6B7280;">{prob.detail}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── MODULE DETAILS ──
    # Using simple stacked containers instead of tabs for a clean, scannable document flow.
    
    # 1. PING
    ping = p.results.get("ping")
    if ping:
        with st.container(border=True):
            st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:16px;'><strong style='font-size:14px;'>Connectivity</strong> {status_indicator(ping.get('status'))}</div>", unsafe_allow_html=True)
            
            pc1, pc2 = st.columns([1, 2])
            with pc1:
                st.markdown(render_kv("Sent", ping.get('sent',0)), unsafe_allow_html=True)
                st.markdown(render_kv("Received", ping.get('received',0)), unsafe_allow_html=True)
                st.markdown(render_kv("Loss", f"{ping.get('packet_loss',0)}%"), unsafe_allow_html=True)
                st.markdown(render_kv("Avg RTT", f"{ping.get('avg_latency',0)} ms"), unsafe_allow_html=True)
                
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
                        height=120,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(visible=False),
                        yaxis=dict(gridcolor="#F3F4F6", title="ms", titlefont=dict(size=11, color="#9CA3AF"), tickfont=dict(size=10, color="#9CA3AF"))
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # 2. TRACEROUTE
    tr = p.results.get("traceroute")
    if tr:
        with st.container(border=True):
            status = "SUCCESS" if tr.get("reached") else "WARNING"
            st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:16px;'><strong style='font-size:14px;'>Routing</strong> {status_indicator(status)}</div>", unsafe_allow_html=True)
            
            hops = tr.get("hops", [])
            if hops:
                df = pd.DataFrame([{
                    "Hop": h["hop"],
                    "IP": h.get("ip") or "*",
                    "Latency (ms)": h.get("latency_ms"),
                } for h in hops])
                
                # Render clean dataframe
                st.dataframe(
                    df, 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Hop": st.column_config.NumberColumn(width="small"),
                        "Latency (ms)": st.column_config.NumberColumn(format="%.1f")
                    }
                )
            else:
                st.markdown("<span style='font-size:13px; color:#6B7280;'>No hops recorded (ICMP likely blocked).</span>", unsafe_allow_html=True)

    # 3. DNS & PORTS
    dns = p.results.get("dns")
    port_d = p.results.get("port")
    
    if dns or port_d:
        colA, colB = st.columns(2)
        with colA:
            if dns:
                with st.container(border=True):
                    status = "SUCCESS" if dns.get("success") else "FAILED"
                    st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:16px;'><strong style='font-size:14px;'>DNS Resolution</strong> {status_indicator(status)}</div>", unsafe_allow_html=True)
                    st.markdown(render_kv("Domain", dns.get("domain", "")), unsafe_allow_html=True)
                    st.markdown(render_kv("Time", f"{dns.get('response_time_ms', 0):.1f} ms"), unsafe_allow_html=True)
                    
                    ips = dns.get("ipv4_addresses", [])
                    if ips:
                        st.markdown(f"<div style='font-size:13px; color:#6B7280; margin-top:8px;'>IPv4 Records</div>", unsafe_allow_html=True)
                        for ip in ips:
                            st.markdown(f"<div style='font-family:\"JetBrains Mono\",monospace; font-size:12px;'>{ip}</div>", unsafe_allow_html=True)
        with colB:
            if port_d:
                with st.container(border=True):
                    st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:16px;'><strong style='font-size:14px;'>Port Scan</strong> <span style='font-size:13px; color:#6B7280;'>{port_d.get('open_count', 0)} open</span></div>", unsafe_allow_html=True)
                    ports_map = port_d.get("ports", {})
                    for p_num in sorted(ports_map.keys(), key=int):
                        info = ports_map[p_num]
                        is_open = info["status"] == "OPEN"
                        c_dot = "#10B981" if is_open else "#EF4444"
                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid #F3F4F6;">
                            <span style="font-family:'JetBrains Mono',monospace; font-size:12px;"><span style="color:{c_dot}; margin-right:6px;">●</span>{p_num}</span>
                            <span style="font-size:12px; color:#6B7280;">{info['service']}</span>
                        </div>
                        """, unsafe_allow_html=True)

    # ── ACTIONS ───────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Raw Data & Export"):
        from reports.report_generator import generate_txt_report, generate_json_report
        t1, t2 = st.columns(2)
        t1.download_button("Download Report (.txt)", generate_txt_report(processed), file_name=f"report_{target}.txt", use_container_width=True)
        t2.download_button("Download Data (.json)", generate_json_report(processed), file_name=f"data_{target}.json", use_container_width=True)
        st.json(p.results)
        
    st.markdown(f"<div style='text-align:right; font-size:11px; color:#9CA3AF; margin-top:16px;'>Execution time: {p.total_time_ms:.0f}ms</div>", unsafe_allow_html=True)
    
elif run:
    st.info("Please enter a valid target to begin.")
