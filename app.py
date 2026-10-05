"""
app.py — Network Diagnostic Toolkit  |  Browser GUI
Run:  streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json, time, sys, os

# ── MUST be first ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NetDiag",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
#  THEME  —  Clean white + electric indigo + amber accents
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }

/* ── Root ── */
html, body, .stApp {
    background: #f5f7fa !important;
    font-family: 'Inter', sans-serif !important;
    color: #1a1d23 !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
[data-testid="collapsedControl"] { display: none; }

/* ── App wrapper ── */
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── TOP NAV BAR ── */
.topbar {
    background: #ffffff;
    border-bottom: 1px solid #e2e6ed;
    padding: 14px 36px;
    display: flex;
    align-items: center;
    gap: 14px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 1px 8px rgba(0,0,0,0.06);
}
.topbar-logo {
    font-size: 22px;
    font-weight: 800;
    color: #4f46e5;
    letter-spacing: -0.5px;
}
.topbar-logo span { color: #f59e0b; }
.topbar-sub {
    font-size: 13px;
    color: #6b7280;
    font-weight: 400;
    border-left: 1px solid #e2e6ed;
    padding-left: 14px;
    margin-left: 2px;
}

/* ── SEARCH BAR ── */
.search-wrap {
    background: #ffffff;
    border-bottom: 1px solid #e2e6ed;
    padding: 20px 36px 20px 36px;
    display: flex;
    gap: 12px;
    align-items: flex-end;
}

/* ── Streamlit input override ── */
.stTextInput > label { font-weight: 600; font-size: 13px; color: #374151; margin-bottom: 6px; }
.stTextInput > div > div > input {
    background: #ffffff !important;
    border: 2px solid #e2e6ed !important;
    border-radius: 10px !important;
    font-size: 15px !important;
    font-family: 'Inter', sans-serif !important;
    color: #1a1d23 !important;
    padding: 10px 16px !important;
    transition: border 0.2s;
}
.stTextInput > div > div > input:focus {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 3px rgba(79,70,229,0.12) !important;
    outline: none !important;
}

/* ── SELECT / SLIDER override ── */
.stSelectbox > label, .stSlider > label { font-weight: 600; font-size: 13px; color: #374151; }
.stSelectbox > div > div {
    background: #ffffff !important;
    border: 2px solid #e2e6ed !important;
    border-radius: 10px !important;
    color: #1a1d23 !important;
}

/* ── BUTTON ── */
.stButton > button {
    background: #4f46e5 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 11px 28px !important;
    letter-spacing: 0.3px;
    transition: all 0.18s;
    box-shadow: 0 2px 8px rgba(79,70,229,0.25) !important;
}
.stButton > button:hover {
    background: #4338ca !important;
    box-shadow: 0 4px 16px rgba(79,70,229,0.35) !important;
    transform: translateY(-1px);
}
.stButton > button:active { transform: translateY(0); }

/* ── MAIN CONTENT AREA ── */
.main-content { padding: 28px 36px; }

/* ── SECTION TITLE ── */
.sec-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #6b7280;
    margin: 28px 0 12px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.sec-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #e2e6ed;
}

/* ── STAT CARDS ── */
.stat-card {
    background: #ffffff;
    border: 1px solid #e2e6ed;
    border-radius: 14px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.2s;
}
.stat-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
.stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent, #4f46e5);
}
.stat-card .label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #9ca3af;
    margin-bottom: 8px;
}
.stat-card .value {
    font-size: 28px;
    font-weight: 800;
    color: var(--accent, #1a1d23);
    line-height: 1;
    font-family: 'JetBrains Mono', monospace;
}
.stat-card .sub {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 5px;
    font-weight: 400;
}

/* ── PANEL ── */
.panel {
    background: #ffffff;
    border: 1px solid #e2e6ed;
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 16px;
}
.panel-title {
    font-size: 13px;
    font-weight: 700;
    color: #374151;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── STATUS CHIPS ── */
.chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 11px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.3px;
}
.chip-green  { background: #dcfce7; color: #15803d; }
.chip-red    { background: #fee2e2; color: #dc2626; }
.chip-amber  { background: #fef3c7; color: #d97706; }
.chip-indigo { background: #e0e7ff; color: #4338ca; }
.chip-gray   { background: #f3f4f6; color: #6b7280; }

/* ── HOP PATH ── */
.hop-path {
    display: flex;
    flex-direction: column;
    gap: 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
}
.hop-row {
    display: grid;
    grid-template-columns: 32px 140px 1fr 80px;
    align-items: center;
    padding: 7px 10px;
    border-radius: 8px;
    transition: background 0.15s;
    gap: 12px;
}
.hop-row:hover { background: #f5f7fa; }
.hop-num {
    font-weight: 700;
    color: #9ca3af;
    font-size: 11px;
}
.hop-ip { color: #4f46e5; }
.hop-lat { text-align: right; font-weight: 600; }
.hop-bar-wrap { height: 6px; background: #f3f4f6; border-radius: 3px; flex: 1; }
.hop-bar { height: 6px; border-radius: 3px; }

/* ── INFO ROWS ── */
.info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #f3f4f6;
    font-size: 13px;
}
.info-row:last-child { border-bottom: none; }
.info-row .key { color: #9ca3af; font-weight: 500; }
.info-row .val { color: #1a1d23; font-weight: 600; font-family: 'JetBrains Mono', monospace; font-size: 12px; }

/* ── PROBLEM ITEMS ── */
.problem {
    padding: 12px 16px;
    border-radius: 10px;
    margin-bottom: 8px;
    border-left: 4px solid;
    font-size: 13px;
}
.problem-critical { background: #fff1f2; border-color: #ef4444; }
.problem-warning  { background: #fffbeb; border-color: #f59e0b; }
.problem-info     { background: #eff6ff; border-color: #3b82f6; }
.problem .ptitle { font-weight: 700; margin-bottom: 3px; }
.problem .pdetail { color: #6b7280; font-size: 12px; }

/* ── REC ITEMS ── */
.rec-item {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 11px 15px;
    margin-bottom: 8px;
    font-size: 13px;
    color: #166534;
    font-weight: 500;
}

/* ── DOWNLOAD BTNS ── */
.stDownloadButton > button {
    background: #ffffff !important;
    border: 2px solid #e2e6ed !important;
    color: #374151 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    width: 100%;
    transition: all 0.18s;
}
.stDownloadButton > button:hover {
    border-color: #4f46e5 !important;
    color: #4f46e5 !important;
    background: #f5f3ff !important;
}

/* ── EXPANDER ── */
.streamlit-expanderHeader {
    background: #f9fafb !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    color: #374151 !important;
}

/* ── DATAFRAME ── */
.stDataFrame { border-radius: 10px; overflow: hidden; }
[data-testid="stDataFrame"] { border: 1px solid #e2e6ed; border-radius: 10px; }

/* ── PROGRESS ── */
.stProgress > div > div > div > div { background: #4f46e5; }

/* ── ALERTS ── */
.stAlert { border-radius: 10px !important; }

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] { background: #f5f7fa; border-radius: 10px; padding: 4px; gap: 2px; }
.stTabs [data-baseweb="tab"] { border-radius: 7px; font-weight: 600; font-size: 13px; color: #6b7280; }
.stTabs [aria-selected="true"] { background: #4f46e5 !important; color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

PLOTLY_BASE = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f9fafb",
    font=dict(family="Inter, sans-serif", color="#374151", size=12),
    margin=dict(l=8, r=8, t=36, b=8),
)

def chip(label, kind="indigo"):
    icons = {"green":"●","red":"●","amber":"●","indigo":"●","gray":"●"}
    return f'<span class="chip chip-{kind}">{icons[kind]} {label}</span>'

def status_chip(s):
    s = (s or "").upper()
    if s in ("HEALTHY","SUCCESS","OPEN","OK","RESOLVED"):   return chip(s,"green")
    if s in ("DEGRADED","WARNING"):                          return chip(s,"amber")
    if s in ("CRITICAL","FAILED","CLOSED","UNREACHABLE"):   return chip(s,"red")
    return chip(s,"gray")

def stat_card(label, value, sub="", accent="#4f46e5"):
    return f"""
    <div class="stat-card" style="--accent:{accent}">
        <div class="label">{label}</div>
        <div class="value" style="color:{accent}">{value}</div>
        {"<div class='sub'>"+sub+"</div>" if sub else ""}
    </div>"""

def info_row(k, v):
    return f'<div class="info-row"><span class="key">{k}</span><span class="val">{v}</span></div>'

def score_accent(s):
    if s >= 85: return "#16a34a"
    if s >= 60: return "#d97706"
    return "#dc2626"

def plotly_fig(**kwargs):
    fig = go.Figure(**kwargs)
    fig.update_layout(**PLOTLY_BASE)
    return fig

# ═══════════════════════════════════════════════════════════════════════════════
#  TOP NAV
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="topbar">
    <div class="topbar-logo">Net<span>Diag</span></div>
    <div class="topbar-sub">Network Diagnostic Toolkit &nbsp;·&nbsp; CN Project</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  SEARCH BAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.container():
    col_q, col_intent, col_btn = st.columns([4, 2, 1])

    with col_q:
        query = st.text_input(
            "Target",
            placeholder='google.com  ·  8.8.8.8  ·  "Why is github.com slow?"',
            value=st.session_state.get("qval", ""),
            key="qval",
            label_visibility="visible",
        )
    with col_intent:
        intent_opt = st.selectbox(
            "Mode",
            ["Auto Detect","Full Scan","Connectivity","Performance",
             "Slow / Latency","HTTPS Check","HTTP Check","SSH Check",
             "DNS Only","Route Only"],
            label_visibility="visible",
        )
        INTENT_MAP = {
            "Auto Detect":"auto","Full Scan":"full","Connectivity":"connectivity",
            "Performance":"performance","Slow / Latency":"slow",
            "HTTPS Check":"https","HTTP Check":"http","SSH Check":"ssh",
            "DNS Only":"dns","Route Only":"route",
        }
    with col_btn:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        run = st.button("⚡ Scan", use_container_width=True)

# Advanced options in expander below search bar
with st.expander("⚙️ Advanced options", expanded=False):
    adv1, adv2 = st.columns(2)
    with adv1:
        ping_count = st.slider("Ping packets", 2, 10, 4)
        ports_raw  = st.text_input("Ports to scan", "22, 53, 80, 443, 8080")
    with adv2:
        save_fmts  = st.multiselect("Auto-save report", ["txt","json"])
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
#  RUN DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════
if run and query.strip():

    try:
        ports = [int(p.strip()) for p in ports_raw.split(",") if p.strip()]
    except ValueError:
        ports = [22, 53, 80, 443, 8080]

    # ── Progress ──────────────────────────────────────────────────────────
    prog_ph  = st.empty()
    prog_bar = st.progress(0)

    def upd(msg, pct):
        prog_ph.markdown(
            f'<p style="font-size:13px;color:#6b7280;margin:4px 0">⏳ {msg}</p>',
            unsafe_allow_html=True
        )
        prog_bar.progress(pct)

    upd("Parsing query…", 5)
    from analysis.diagnosis import parse_query
    parsed = parse_query(query.strip())
    target = parsed.target or query.strip()
    intent = INTENT_MAP[intent_opt] if intent_opt != "Auto Detect" else parsed.intent

    upd(f"Validating {target}…", 15)
    from core.validator import validate
    val = validate(target)

    if not val.is_valid:
        prog_ph.empty(); prog_bar.empty()
        st.error(f"❌ {val.error}")
        st.stop()

    upd("Running diagnostics…", 30)
    from core.diagnostic_engine import DiagnosticEngine
    engine  = DiagnosticEngine(val)
    payload = engine.run(intent=intent, custom_ports=ports, ping_count=ping_count)

    upd("Analyzing…", 88)
    from core.result_processor import ResultProcessor
    processed = ResultProcessor().process(payload)

    # Save
    saved = {}
    if save_fmts:
        from reports.report_generator import save_report
        for f in save_fmts:
            saved[f] = save_report(processed, fmt=f)

    upd("Done", 100)
    time.sleep(0.25)
    prog_ph.empty(); prog_bar.empty()

    p = payload
    ping     = p.results.get("ping", {})
    dns      = p.results.get("dns", {})
    tr       = p.results.get("traceroute", {})
    port_d   = p.results.get("port", {})
    net_info = p.results.get("network_info", {})
    score    = processed.health_score
    acc      = score_accent(score)

    # NL banner
    if parsed.natural_language:
        st.info(f'💬 **"{query}"** → target: `{target}` · intent: `{intent}`')

    # ═══════════════════════════════════════════════════════════════════════
    #  OVERVIEW STAT CARDS
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sec-title">Overview</div>', unsafe_allow_html=True)

    oc1, oc2, oc3, oc4, oc5 = st.columns(5)

    with oc1:
        st.markdown(stat_card("Target", p.target, sub=f"→ {p.resolved_ip}", accent="#4f46e5"),
                    unsafe_allow_html=True)
    with oc2:
        lat = ping.get("avg_latency", 0)
        lat_acc = "#16a34a" if lat < 80 else ("#d97706" if lat < 200 else "#dc2626")
        st.markdown(stat_card("Avg Latency", f"{lat} ms",
                              sub=f"min {ping.get('min_latency',0)} · max {ping.get('max_latency',0)}",
                              accent=lat_acc), unsafe_allow_html=True)
    with oc3:
        loss = ping.get("packet_loss", 0)
        loss_acc = "#16a34a" if loss == 0 else ("#d97706" if loss < 10 else "#dc2626")
        st.markdown(stat_card("Packet Loss", f"{loss}%",
                              sub=f"{ping.get('received',0)}/{ping.get('sent',0)} received",
                              accent=loss_acc), unsafe_allow_html=True)
    with oc4:
        nhops = tr.get("total_hops", 0)
        st.markdown(stat_card("Hops", str(nhops) if nhops else "—",
                              sub="traceroute", accent="#7c3aed"), unsafe_allow_html=True)
    with oc5:
        st.markdown(stat_card("Health", f"{score}/100",
                              sub=processed.overall_status, accent=acc),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    #  TABS
    # ═══════════════════════════════════════════════════════════════════════
    tabs = st.tabs(["📡 Ping", "🗺️ Traceroute", "🔍 DNS & Ports",
                    "🖥️ Network", "🩺 Diagnosis", "📄 Reports"])

    # ───────────────────────────────────────────────────────────────────────
    #  TAB 1 — PING
    # ───────────────────────────────────────────────────────────────────────
    with tabs[0]:
        if ping:
            st.markdown(f"""
            <div class="panel">
                <div class="panel-title">📡 Ping Results &nbsp; {status_chip(ping.get('status',''))}</div>
                {info_row("Target", ping.get('target','—'))}
                {info_row("Packets Sent", str(ping.get('sent',0)))}
                {info_row("Packets Received", str(ping.get('received',0)))}
                {info_row("Packet Loss", f"{ping.get('packet_loss',0)}%")}
                {info_row("Min Latency", f"{ping.get('min_latency',0)} ms")}
                {info_row("Avg Latency", f"{ping.get('avg_latency',0)} ms")}
                {info_row("Max Latency", f"{ping.get('max_latency',0)} ms")}
            </div>
            """, unsafe_allow_html=True)

            raw = ping.get("raw_times", [])
            c1, c2 = st.columns([3, 2])

            with c1:
                if raw:
                    fig = plotly_fig()
                    x = list(range(1, len(raw)+1))
                    fig.add_trace(go.Scatter(
                        x=x, y=raw,
                        mode="lines+markers",
                        line=dict(color="#4f46e5", width=2.5),
                        marker=dict(size=9, color="#4f46e5",
                                    line=dict(color="#ffffff", width=2)),
                        fill="tozeroy",
                        fillcolor="rgba(79,70,229,0.07)",
                        name="RTT (ms)",
                    ))
                    if len(raw) > 1:
                        avg = sum(raw)/len(raw)
                        fig.add_hline(y=avg, line_dash="dot",
                                      line_color="#f59e0b", line_width=1.5,
                                      annotation_text=f" avg {avg:.1f}ms",
                                      annotation_font_color="#f59e0b",
                                      annotation_position="right")
                    fig.update_layout(
                        title=dict(text="Round-Trip Time", font=dict(size=13, color="#374151")),
                        xaxis_title="Ping #", yaxis_title="Latency (ms)",
                        height=280, showlegend=False,
                        xaxis=dict(dtick=1, gridcolor="#f3f4f6"),
                        yaxis=dict(gridcolor="#f3f4f6"),
                        **PLOTLY_BASE
                    )
                    st.plotly_chart(fig, use_container_width=True)

            with c2:
                recv = ping.get("received",0)
                lost = ping.get("lost",0)
                if recv + lost > 0:
                    fig2 = go.Figure(go.Pie(
                        labels=["Received", "Lost"],
                        values=[recv, max(lost,0)],
                        marker_colors=["#4f46e5", "#f87171"],
                        hole=0.62,
                        textinfo="percent",
                        textfont=dict(size=13, color="#374151"),
                        hovertemplate="%{label}: %{value}<extra></extra>",
                    ))
                    fig2.update_layout(
                        title=dict(text="Packet Distribution", font=dict(size=13, color="#374151")),
                        annotations=[dict(
                            text=f"<b>{recv}</b><br>recv",
                            x=0.5, y=0.5, showarrow=False,
                            font=dict(size=15, color="#4f46e5"),
                        )],
                        height=280, showlegend=True,
                        legend=dict(orientation="h", y=-0.1),
                        **PLOTLY_BASE
                    )
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Ping was not run for this intent.")

    # ───────────────────────────────────────────────────────────────────────
    #  TAB 2 — TRACEROUTE
    # ───────────────────────────────────────────────────────────────────────
    with tabs[1]:
        if tr:
            hops = tr.get("hops", [])
            reached_chip = status_chip("SUCCESS" if tr.get("reached") else "WARNING")
            st.markdown(f"""
            <div class="panel">
                <div class="panel-title">🗺️ Traceroute &nbsp; {reached_chip}
                    &nbsp; <span style='font-weight:400;color:#9ca3af'>{tr.get('total_hops',0)} hops</span>
                </div>
            """, unsafe_allow_html=True)

            if hops:
                # Hop path visualizer
                max_lat = max((h["latency_ms"] for h in hops if h.get("latency_ms")), default=1)
                html_hops = '<div class="hop-path">'
                html_hops += f"""
                <div class="hop-row" style="font-weight:700;color:#9ca3af;font-size:10px;
                     text-transform:uppercase;letter-spacing:1px;padding-bottom:4px">
                    <span>#</span><span>IP Address</span><span>Hostname</span><span>Latency</span>
                </div>"""
                for h in hops:
                    ip  = h.get("ip") or "* * *"
                    hn  = (h.get("hostname") or "")[:32]
                    if hn == ip: hn = "—"
                    lat = h.get("latency_ms")
                    if h.get("timed_out") or lat is None:
                        lat_str = "timeout"
                        bar_pct = 0
                        lat_col = "#9ca3af"
                    else:
                        lat_str = f"{lat:.1f} ms"
                        bar_pct = int((lat / max_lat) * 100)
                        # spike detection
                        lat_col = "#4f46e5" if lat < max_lat * 0.6 else "#f59e0b" if lat < max_lat * 0.85 else "#ef4444"

                    bar_color = lat_col
                    html_hops += f"""
                    <div class="hop-row">
                        <span class="hop-num">{h['hop']:02d}</span>
                        <span class="hop-ip">{ip}</span>
                        <span style="color:#6b7280;font-size:11px">{hn or '—'}</span>
                        <span class="hop-lat" style="color:{lat_col}">{lat_str}</span>
                    </div>
                    <div style="padding:0 10px 4px 54px">
                        <div class="hop-bar-wrap">
                            <div class="hop-bar" style="width:{bar_pct}%;background:{bar_color}"></div>
                        </div>
                    </div>"""

                html_hops += '</div></div>'
                st.markdown(html_hops, unsafe_allow_html=True)

                # Chart
                valid = [h for h in hops if h.get("latency_ms") is not None]
                if valid:
                    lats = [h["latency_ms"] for h in valid]
                    ips  = [h.get("ip") or "*" for h in valid]
                    hnms = [h.get("hostname") or h.get("ip") or "*" for h in valid]
                    cols = []
                    prev = 0.0
                    for lat in lats:
                        delta = lat - prev
                        cols.append("#ef4444" if delta > 50 else "#4f46e5")
                        prev = lat

                    fig3 = go.Figure(go.Bar(
                        x=[h["hop"] for h in valid],
                        y=lats,
                        marker_color=cols,
                        text=[f"{l:.0f}ms" for l in lats],
                        textposition="outside",
                        customdata=ips,
                        hovertemplate="Hop %{x} · %{customdata}<br>%{y:.1f} ms<extra></extra>",
                    ))
                    fig3.update_layout(
                        title=dict(text="Latency per Hop  <span style='color:#ef4444;font-size:11px'>● spike</span>  <span style='color:#4f46e5;font-size:11px'>● normal</span>",
                                   font=dict(size=13, color="#374151")),
                        xaxis_title="Hop", yaxis_title="ms",
                        height=240,
                        xaxis=dict(tickmode="linear", gridcolor="#f3f4f6"),
                        yaxis=dict(gridcolor="#f3f4f6"),
                        bargap=0.35,
                        **PLOTLY_BASE
                    )
                    st.plotly_chart(fig3, use_container_width=True)
            else:
                st.warning("No hops returned — firewall may be blocking ICMP.")
        else:
            st.info("Traceroute was not run for this intent.")

    # ───────────────────────────────────────────────────────────────────────
    #  TAB 3 — DNS & PORTS
    # ───────────────────────────────────────────────────────────────────────
    with tabs[2]:
        dns_col, port_col = st.columns([1, 1], gap="large")

        with dns_col:
            if dns:
                dns_chip = status_chip("SUCCESS" if dns.get("success") else "FAILED")
                st.markdown(f"""
                <div class="panel">
                    <div class="panel-title">🔍 DNS &nbsp; {dns_chip}</div>
                    {info_row("Domain", dns.get('domain','—'))}
                    {info_row("Response Time", f"{dns.get('response_time_ms',0):.1f} ms")}
                    {"".join(info_row("IPv4",ip) for ip in dns.get('ipv4_addresses',[]))}
                    {"".join(info_row("IPv6",ip) for ip in dns.get('ipv6_addresses',[]))}
                    {"<div style='margin-top:8px;padding:10px;background:#fff1f2;border-radius:8px;font-size:12px;color:#dc2626'>" + dns.get('error','') + "</div>" if not dns.get('success') else ""}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("DNS not run.")

        with port_col:
            if port_d:
                ports_map = port_d.get("ports", {})
                open_c  = port_d.get("open_count", 0)
                cls_c   = port_d.get("closed_count", 0)
                st.markdown(f"""
                <div class="panel">
                    <div class="panel-title">🔌 Port Scan
                        &nbsp; <span style="color:#16a34a;font-weight:700">{open_c} open</span>
                        &nbsp; <span style="color:#9ca3af">·</span>
                        &nbsp; <span style="color:#dc2626;font-weight:700">{cls_c} closed</span>
                    </div>
                """, unsafe_allow_html=True)

                for port_str in sorted(ports_map.keys(), key=int):
                    info   = ports_map[port_str]
                    is_open = info["status"] == "OPEN"
                    dot     = '<span style="color:#16a34a">●</span>' if is_open else '<span style="color:#dc2626">●</span>'
                    bg      = "#f0fdf4" if is_open else "#fff8f8"
                    tc      = "#166534" if is_open else "#991b1b"
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;align-items:center;
                         padding:9px 12px;border-radius:8px;margin-bottom:5px;background:{bg}">
                        <span style="font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:600;color:{tc}">
                            {dot} &nbsp; :{port_str}
                        </span>
                        <span style="font-size:12px;color:#6b7280">{info['service']}</span>
                        <span style="font-size:12px;font-weight:700;color:{tc}">{info['status']}</span>
                    </div>""", unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

                # Mini donut
                fig_p = go.Figure(go.Pie(
                    labels=["Open","Closed"],
                    values=[max(open_c,0), max(cls_c,0)],
                    marker_colors=["#4f46e5","#f3f4f6"],
                    hole=0.65, textinfo="percent",
                    hovertemplate="%{label}: %{value}<extra></extra>",
                ))
                fig_p.update_layout(
                    title=dict(text="Port Status", font=dict(size=12)),
                    height=200, showlegend=False,
                    annotations=[dict(text=f"<b>{open_c}</b><br>open", x=0.5, y=0.5,
                                      showarrow=False, font=dict(size=14, color="#4f46e5"))],
                    **PLOTLY_BASE
                )
                st.plotly_chart(fig_p, use_container_width=True)
            else:
                st.info("Port scan not run.")

    # ───────────────────────────────────────────────────────────────────────
    #  TAB 4 — NETWORK INFO
    # ───────────────────────────────────────────────────────────────────────
    with tabs[3]:
        if net_info:
            ni1, ni2 = st.columns(2)
            with ni1:
                st.markdown(f"""
                <div class="panel">
                    <div class="panel-title">🖥️ Local Machine</div>
                    {info_row("Hostname",   net_info.get('hostname','—'))}
                    {info_row("Local IP",   net_info.get('local_ip','—'))}
                    {info_row("Subnet Mask",net_info.get('subnet_mask') or '—')}
                </div>""", unsafe_allow_html=True)
            with ni2:
                st.markdown(f"""
                <div class="panel">
                    <div class="panel-title">🌐 Gateway & DNS</div>
                    {info_row("Default Gateway", net_info.get('default_gateway') or '—')}
                    {info_row("DNS Servers", ', '.join(net_info.get('dns_servers',[])))}
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Network info not collected for this intent.")

    # ───────────────────────────────────────────────────────────────────────
    #  TAB 5 — DIAGNOSIS
    # ───────────────────────────────────────────────────────────────────────
    with tabs[4]:
        dg1, dg2 = st.columns([1, 1], gap="large")

        with dg1:
            # Health gauge
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                gauge=dict(
                    axis=dict(range=[0,100], tickfont=dict(size=11, color="#9ca3af"),
                              tickcolor="#e2e6ed"),
                    bar=dict(color=acc, thickness=0.22),
                    bgcolor="#f9fafb",
                    bordercolor="#e2e6ed",
                    borderwidth=1,
                    steps=[
                        dict(range=[0,60],  color="#fee2e2"),
                        dict(range=[60,85], color="#fef3c7"),
                        dict(range=[85,100],color="#dcfce7"),
                    ],
                    threshold=dict(
                        line=dict(color=acc, width=3),
                        value=score,
                    ),
                ),
                title=dict(text="Health Score", font=dict(size=13, color="#6b7280")),
                number=dict(suffix="/100", font=dict(size=36, color=acc, family="JetBrains Mono")),
            ))
            fig_g.update_layout(height=260, **PLOTLY_BASE)
            st.plotly_chart(fig_g, use_container_width=True)

            # Module score bars
            if processed.module_scores:
                from core.result_processor import WEIGHTS
                fig_ms = go.Figure()
                mods  = list(processed.module_scores.keys())
                earned= [processed.module_scores[m] for m in mods]
                max_s = [WEIGHTS.get(m, 10) for m in mods]
                fig_ms.add_trace(go.Bar(
                    name="Max", x=mods, y=max_s,
                    marker_color="#f3f4f6", width=0.5,
                ))
                fig_ms.add_trace(go.Bar(
                    name="Earned", x=mods, y=earned,
                    marker_color="#4f46e5", width=0.5,
                ))
                fig_ms.update_layout(
                    barmode="overlay",
                    title=dict(text="Module Scores", font=dict(size=12)),
                    height=200, showlegend=False,
                    yaxis=dict(gridcolor="#f3f4f6"),
                    bargap=0.3,
                    **PLOTLY_BASE
                )
                st.plotly_chart(fig_ms, use_container_width=True)

        with dg2:
            st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

            # Problems
            sev_cls = {"critical":"problem-critical","warning":"problem-warning","info":"problem-info"}
            if processed.problems:
                st.markdown("**Problems**")
                for prob in processed.problems:
                    cls = sev_cls.get(prob.severity, "problem-info")
                    st.markdown(f"""
                    <div class="problem {cls}">
                        <div class="ptitle">[{prob.severity.upper()}] {prob.description}</div>
                        <div class="pdetail">{prob.detail}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;
                     padding:20px;text-align:center;color:#166534;font-weight:600">
                    ✅ No problems detected
                </div>""", unsafe_allow_html=True)

            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

            # Causes
            if processed.possible_causes:
                st.markdown("**Possible Causes**")
                for c in processed.possible_causes:
                    st.markdown(
                        f'<div style="font-size:13px;color:#6b7280;padding:5px 0 5px 12px;'
                        f'border-left:2px solid #e2e6ed">⚠ {c}</div>',
                        unsafe_allow_html=True)

            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

            # Recommendations
            if processed.recommendations:
                st.markdown("**Recommendations**")
                for r in processed.recommendations:
                    st.markdown(f'<div class="rec-item">→ {r}</div>', unsafe_allow_html=True)

    # ───────────────────────────────────────────────────────────────────────
    #  TAB 6 — REPORTS
    # ───────────────────────────────────────────────────────────────────────
    with tabs[5]:
        from reports.report_generator import generate_txt_report, generate_json_report
        txt_data  = generate_txt_report(processed)
        json_data = generate_json_report(processed)

        st.markdown('<div class="sec-title">Download</div>', unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        with r1:
            st.download_button("⬇ TXT Report", txt_data,
                               f"report_{p.target.replace('.','_')}.txt",
                               "text/plain", use_container_width=True)
        with r2:
            st.download_button("⬇ JSON Report", json_data,
                               f"report_{p.target.replace('.','_')}.json",
                               "application/json", use_container_width=True)
        with r3:
            st.download_button("⬇ Raw Data",
                               json.dumps(p.results, indent=2, default=str),
                               f"raw_{p.target.replace('.','_')}.json",
                               "application/json", use_container_width=True)

        if saved:
            st.markdown('<div class="sec-title">Saved to Disk</div>', unsafe_allow_html=True)
            for fmt, path in saved.items():
                st.code(path, language=None)

        st.markdown('<div class="sec-title">TXT Preview</div>', unsafe_allow_html=True)
        st.text(txt_data)

        with st.expander("JSON Preview"):
            st.json(p.results)

    # Timing
    st.markdown(
        f'<p style="font-size:11px;color:#d1d5db;text-align:right;margin-top:16px">'
        f'Scan completed in {p.total_time_ms:.0f} ms</p>',
        unsafe_allow_html=True
    )

elif run:
    st.warning("Please enter a domain or IP address.")

else:
    # ── Landing page ────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding: 60px 0; text-align: center;">
        <div style="font-size: 56px; margin-bottom: 16px">⚡</div>
        <h2 style="font-size: 24px; font-weight: 800; color: #1a1d23; margin: 0 0 10px 0">
            Type a target above to begin
        </h2>
        <p style="color: #6b7280; font-size: 15px; margin: 0 0 40px 0">
            Supports <code style="background:#f3f4f6;padding:2px 7px;border-radius:5px">google.com</code>
            &nbsp;·&nbsp;
            <code style="background:#f3f4f6;padding:2px 7px;border-radius:5px">8.8.8.8</code>
            &nbsp;·&nbsp;
            <code style="background:#f3f4f6;padding:2px 7px;border-radius:5px">"Why is X slow?"</code>
        </p>
        <div style="display:flex; justify-content:center; gap:16px; flex-wrap:wrap">
    """, unsafe_allow_html=True)

    features = [
        ("📡", "Ping", "Latency, packet loss, RTT chart"),
        ("🗺️", "Traceroute", "Hop-by-hop path analysis"),
        ("🔍", "DNS", "A & AAAA resolution timing"),
        ("🔌", "Port Scan", "TCP service availability"),
        ("🖥️", "Network Info", "Local IP, gateway, DNS"),
        ("🩺", "Diagnosis", "Smart rules engine + score"),
    ]
    cols = st.columns(len(features))
    for col, (icon, title, desc) in zip(cols, features):
        with col:
            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e6ed;border-radius:14px;
                 padding:22px 16px;text-align:center;transition:box-shadow 0.2s">
                <div style="font-size:28px;margin-bottom:10px">{icon}</div>
                <div style="font-weight:700;font-size:14px;color:#1a1d23;margin-bottom:5px">{title}</div>
                <div style="font-size:12px;color:#9ca3af">{desc}</div>
            </div>""", unsafe_allow_html=True)
