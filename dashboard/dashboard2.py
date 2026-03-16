"""
dashboard.py  —  CCFA Phase 4  (v2.0)
──────────────────────────────────────
Minimal, whitespace-heavy compliance dashboard.

Sections:
  0. Sidebar   — simulation controls + live re-run
  1. Header    — transaction ID + risk badge
  2. KPIs      — 5 headline numbers
  3. Transaction Details Panel  — sender / receiver / intermediary hops
  4. Agent Debate Visualizer    — step-by-step courtroom timeline
  5. SHAP chart + Cycle motif graph
  6. Regulatory breach table
  7. Compliance KPI metrics over time (historical mock)
  8. SAR receipts + reasoning trace
  9. LIME explanation + PDF download

Run:
    streamlit run dashboard/dashboard.py
"""

import sys, os, math, random, copy
from datetime import datetime, timezone, timedelta

# Works whether dashboard.py lives in project root OR dashboard/ subfolder
_here = os.path.dirname(os.path.abspath(__file__))
_root = _here if os.path.isdir(os.path.join(_here, "agents")) else os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd
except ImportError:
    print("Install:  pip install streamlit plotly pandas")
    sys.exit(0)

from agents.orchestrator import run_pipeline
from xai.xai_engine import explain
from data.context_package import CONTEXT_PACKAGE


# ─────────────────────────────────────────────────────────────────────────────
# Design tokens
# ─────────────────────────────────────────────────────────────────────────────

BG      = "#F7F7F7"
SURFACE = "#FFFFFF"
BORDER  = "#E4E4E4"
T_PRI   = "#111111"
T_SEC   = "#555555"
T_FAINT = "#AAAAAA"
RED     = "#C0392B"
GREEN   = "#1A7F4B"
BLUE    = "#0057FF"
MONO    = "'IBM Plex Mono', monospace"
SANS    = "'Inter', sans-serif"


# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CCFA · Compliance Dashboard",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"]           {{ font-family: {SANS}; color: {T_PRI}; }}
.stApp                               {{ background: {BG}; }}
section[data-testid="stSidebar"]     {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}
.block-container                     {{ padding-top: 2rem; }}
.lbl {{
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.13em;
    text-transform: uppercase; color: {T_FAINT}; margin-bottom: 0.5rem; display: block;
}}
.stat {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 1rem 1.1rem;
}}
.stat-val {{ font-size: 1.55rem; font-weight: 600; letter-spacing:-0.03em; line-height:1.1; }}
.stat-sub {{ font-size: 0.72rem; margin-top: 3px; }}
.stat-bad  {{ color: {RED}; }}
.stat-good {{ color: {GREEN}; }}
.pill {{
    display:inline-block; font-size:0.68rem; font-weight:600;
    letter-spacing:0.09em; text-transform:uppercase;
    padding: 3px 11px; border-radius: 20px; color: #fff;
}}
.pill-h {{ background: {RED}; }}
.pill-l {{ background: {GREEN}; }}
.ecard {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 1rem 1.1rem;
}}
.ename {{ font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem; }}
.erow  {{ font-size: 0.78rem; color: {T_SEC}; margin: 0.18rem 0; }}
.eflag {{ color: {RED}; font-weight: 600; }}
.hcard {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-left: 3px solid {RED};
    border-radius: 8px; padding: 0.9rem 1rem;
}}
.fbadge {{
    display: inline-block; font-size: 0.7rem; font-weight: 600;
    padding: 3px 10px; border-radius: 20px; margin-right: 6px; margin-top: 6px;
}}
.debate-step {{
    border-left: 2px solid {BORDER};
    padding: 0 0 1.6rem 1.4rem;
    margin-left: 0.5rem;
    position: relative;
}}
.debate-step:last-child {{ border-left: 2px solid transparent; padding-bottom: 0; }}
.ddot {{
    position: absolute; left: -5px; top: 3px;
    width: 8px; height: 8px; border-radius: 50%;
}}
.dagent {{
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: {T_FAINT}; margin-bottom: 0.35rem;
    display: flex; align-items: center; gap: 8px;
}}
.dtools {{ display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 0.5rem; }}
.dtool  {{
    font-size: 0.67rem; font-family: {MONO};
    background: {BG}; border: 1px solid {BORDER};
    border-radius: 4px; padding: 2px 7px; color: {BLUE};
}}
.dverdict {{
    font-size: 0.8rem; font-family: {MONO};
    background: {BG}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 0.75rem 0.9rem;
    white-space: pre-wrap; line-height: 1.65; color: {T_PRI};
}}
.brow {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 0.5rem;
    display: grid; grid-template-columns: 11rem 5.5rem 1fr 11rem;
    align-items: start; gap: 1rem;
}}
.brule   {{ font-family: {MONO}; font-size: 0.75rem; color: {T_SEC}; }}
.breach  {{ color: {RED};   font-size: 0.72rem; font-weight: 700; }}
.bclean  {{ color: {GREEN}; font-size: 0.72rem; font-weight: 700; }}
.breason {{ font-size: 0.78rem; color: {T_SEC}; }}
.bpen    {{ font-size: 0.72rem; color: {T_FAINT}; text-align: right; }}
.sarcard {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem;
}}
.sarid   {{ font-family: {MONO}; font-size: 0.75rem; color: {T_SEC}; }}
.sarmeta {{ font-size: 0.75rem; color: {T_FAINT}; margin-top: 0.2rem; }}
.trow {{
    display: flex; align-items: center; gap: 0.8rem;
    padding: 0.45rem 0; border-bottom: 1px solid {BORDER};
    font-size: 0.78rem;
}}
.tnode {{ width: 9rem; font-weight: 500; color: {T_PRI}; flex-shrink: 0; }}
.ttool {{ font-family: {MONO}; color: {BLUE}; flex: 1; font-size: 0.72rem; }}
.tms   {{ color: {T_FAINT}; font-family: {MONO}; font-size: 0.72rem; width: 4rem; text-align: right; flex-shrink: 0; }}
[data-testid="stMetricValue"] {{ display: none; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def stat(label, value, sub="", bad=True):
    sub_cls  = "stat-bad" if bad else "stat-good"
    sub_html = f'<div class="stat-sub {sub_cls}">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="stat">
      <div class="lbl">{label}</div>
      <div class="stat-val">{value}</div>
      {sub_html}
    </div>""", unsafe_allow_html=True)


def pill(text, high=True):
    return f'<span class="pill {"pill-h" if high else "pill-l"}">{text}</span>'


def hr():
    st.markdown("<hr style='border:none;border-top:1px solid #E4E4E4;margin:2rem 0'>",
                unsafe_allow_html=True)


def build_pkg(amount, s_age, r_age, anomaly, shell):
    pkg = copy.deepcopy(CONTEXT_PACKAGE)
    pkg["transaction"]["amount_usd"]                   = amount
    pkg["transaction"]["sender"]["account_age_days"]   = s_age
    pkg["transaction"]["receiver"]["account_age_days"] = r_age
    pkg["graph_analysis"]["anomaly_score"]              = round(anomaly, 2)
    pkg["graph_analysis"]["shell_company_probability"]  = round(shell, 2)
    return pkg


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"<div style='font-size:1.1rem;font-weight:600;margin-bottom:2px'>⚖️ CCFA</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.75rem;color:{T_FAINT};margin-bottom:1rem'>Cognitive Compliance & Forensic Auditor</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f'<span class="lbl">Simulation Controls</span>', unsafe_allow_html=True)
    amount  = st.slider("Transaction Amount ($)",      1_000,  200_000, 47_500, step=500)
    s_age   = st.slider("Sender Account Age (days)",      10,      500,     94)
    r_age   = st.slider("Receiver Account Age (days)",    10,      500,     61)
    anomaly = st.slider("GNN Anomaly Score",             0.0,      1.0,   0.91, step=0.01)
    shell   = st.slider("Shell Company Probability",     0.0,      1.0,   0.87, step=0.01)
    st.markdown("---")
    run_btn = st.button("▶  Run Analysis", type="primary", use_container_width=True)
    st.markdown("---")
    st.markdown(f'<span class="lbl">Pipeline Agents</span>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style='font-size:0.78rem;line-height:2.1;color:{T_SEC}'>
    🇮🇳 &nbsp;IndiaExpert &nbsp;<span style='color:{T_FAINT}'>RBI</span><br>
    🇪🇺 &nbsp;EUExpert &nbsp;<span style='color:{T_FAINT}'>AMLD-6 / EU AI Act</span><br>
    ⚖️ &nbsp;Auditor &nbsp;<span style='color:{T_FAINT}'>Final ruling</span>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Phases 1 & 2 not connected — mock data.")


# ─────────────────────────────────────────────────────────────────────────────
# Session state — run pipeline
# ─────────────────────────────────────────────────────────────────────────────

if "fs" not in st.session_state or run_btn:
    pkg = build_pkg(amount, s_age, r_age, anomaly, shell)
    with st.spinner("Running courtroom pipeline…"):
        st.session_state.fs  = run_pipeline(pkg)
        st.session_state.xai = explain(st.session_state.fs)

fs  = st.session_state.fs
xai = st.session_state.xai
txn = fs["transaction"]
g   = fs["graph_analysis"]


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Header
# ─────────────────────────────────────────────────────────────────────────────

c_title, c_badge = st.columns([6, 1])
with c_title:
    st.markdown(f"<h2 style='margin-bottom:2px'>{txn['id']}</h2>", unsafe_allow_html=True)
    st.markdown(
        f"<span style='font-size:0.78rem;color:{T_FAINT}'>"
        f"Run &nbsp;<code>{fs.get('run_id','—')[:20]}…</code>"
        f"&nbsp;·&nbsp; {fs.get('completed_at','—')[:19]}</span>",
        unsafe_allow_html=True,
    )
with c_badge:
    is_high = xai.model_prediction == "HIGH RISK"
    st.markdown(
        f"<div style='text-align:right;padding-top:18px'>"
        f"{pill(xai.model_prediction, is_high)}</div>",
        unsafe_allow_html=True,
    )
hr()


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — KPI strip
# ─────────────────────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)
with k1: stat("Amount",            f"${txn['amount_usd']:,.0f}", "Cross-border wire",    bad=True)
with k2: stat("GNN Anomaly",       f"{g['anomaly_score']:.2f}",  "High risk zone",       bad=g['anomaly_score'] > 0.75)
with k3: stat("Shell Probability", f"{g['shell_company_probability']:.0%}", "Above 80%", bad=g['shell_company_probability'] > 0.8)
with k4: stat("Confidence",        f"{xai.model_confidence:.0%}", "Auditor certainty",   bad=False)
with k5: stat("SARs Filed",        str(len(fs.get("sar_filings", []))), "RBI · EU GoAML", bad=False)
hr()


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — Transaction Details Panel
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<span class="lbl">Transaction Details</span>', unsafe_allow_html=True)

sender   = txn["sender"]
receiver = txn["receiver"]
hops     = txn.get("intermediary_hops", [])

c_s, c_arr, c_r = st.columns([5, 1, 5])

with c_s:
    kyc_s  = f'<span class="eflag">⚠ KYC Pending</span>' if sender["account_age_days"] < 180 else f'<span style="color:{GREEN}">✓ KYC OK</span>'
    flag_s = f'<span class="eflag">⚑ {sender["prior_flags"]} prior flag(s)</span>' if sender.get("prior_flags") else ""
    st.markdown(f"""
    <div class="ecard">
      <span class="lbl">Sender</span>
      <div class="ename">{sender['entity_name']}</div>
      <div class="erow">🏦 &nbsp;{sender['bank']}</div>
      <div class="erow">🌐 &nbsp;{sender['country']} &nbsp;·&nbsp; <code>{sender['account_id']}</code></div>
      <div class="erow">📅 &nbsp;Account age: <b>{sender['account_age_days']} days</b></div>
      <div class="erow">💸 &nbsp;Monthly avg: ${sender['monthly_avg_txn']:,}</div>
      <div class="erow" style="margin-top:0.5rem">{kyc_s} &nbsp;&nbsp; {flag_s}</div>
    </div>""", unsafe_allow_html=True)

with c_arr:
    st.markdown(
        f"<div style='display:flex;align-items:center;justify-content:center;"
        f"height:100%;font-size:1.5rem;color:{T_FAINT};padding-top:50px'>→</div>",
        unsafe_allow_html=True,
    )

with c_r:
    kyc_r  = f'<span class="eflag">⚠ KYC Pending</span>' if receiver["account_age_days"] < 180 else f'<span style="color:{GREEN}">✓ KYC OK</span>'
    flag_r = f'<span class="eflag">⚑ {receiver["prior_flags"]} prior flag(s)</span>' if receiver.get("prior_flags") else ""
    st.markdown(f"""
    <div class="ecard">
      <span class="lbl">Receiver</span>
      <div class="ename">{receiver['entity_name']}</div>
      <div class="erow">🏦 &nbsp;{receiver['bank']}</div>
      <div class="erow">🌐 &nbsp;{receiver['country']} &nbsp;·&nbsp; <code>{receiver['account_id']}</code></div>
      <div class="erow">📅 &nbsp;Account age: <b>{receiver['account_age_days']} days</b></div>
      <div class="erow">💸 &nbsp;Monthly avg: ${receiver['monthly_avg_txn']:,}</div>
      <div class="erow" style="margin-top:0.5rem">{kyc_r} &nbsp;&nbsp; {flag_r}</div>
    </div>""", unsafe_allow_html=True)

# Intermediary hops
if hops:
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    st.markdown('<span class="lbl">Intermediary Routing Hops</span>', unsafe_allow_html=True)
    hop_cols = st.columns(len(hops))
    for i, (hop, col) in enumerate(zip(hops, hop_cols)):
        with col:
            st.markdown(f"""
            <div class="hcard">
              <span class="lbl">Hop {i+1}</span>
              <div class="ename" style="font-size:0.82rem">{hop['account_id']}</div>
              <div class="erow">🌐 &nbsp;{hop['country']}</div>
              <div class="erow">⏱ &nbsp;Hold time: <b>{hop['hold_time_hrs']}h</b></div>
              <div class="erow" style="margin-top:0.4rem"><span class="eflag">↯ Rapid transit flag</span></div>
            </div>""", unsafe_allow_html=True)

# Transaction flags
flag_html = ""
if txn.get("velocity_spike"):
    flag_html += f'<span class="fbadge" style="border:1px solid {RED};color:{RED}">⚡ Velocity Spike (3×)</span>'
if not txn.get("device_fingerprint_match"):
    flag_html += f'<span class="fbadge" style="border:1px solid {RED};color:{RED}">🖥 Device Mismatch</span>'
if txn.get("stated_purpose"):
    flag_html += f'<span class="fbadge" style="border:1px solid {GREEN};color:{GREEN}">📋 Purpose Stated</span>'
if flag_html:
    st.markdown(f"<div style='margin-top:0.8rem'>{flag_html}</div>", unsafe_allow_html=True)

hr()


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — Agent Debate Visualizer
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<span class="lbl">Agent Courtroom — Debate Timeline</span>', unsafe_allow_html=True)
st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)

debate_steps = [
    {
        "agent":   "🇮🇳  IndiaExpert  ·  RBI",
        "tools":   ["neo4j_query", "account_lookup", "pinecone_search (RBI)"],
        "verdict": fs.get("india_expert_verdict", "—"),
        "flagged": "HIGH RISK" in fs.get("india_expert_verdict", ""),
    },
    {
        "agent":   "🇪🇺  EUExpert  ·  AMLD-6 / EU AI Act",
        "tools":   ["account_lookup (hops)", "pinecone_search (EU)"],
        "verdict": fs.get("eu_expert_verdict", "—"),
        "flagged": "HIGH RISK" in fs.get("eu_expert_verdict", ""),
    },
    {
        "agent":   "⚖️  Auditor  ·  Final Ruling",
        "tools":   ["sar_filing (RBI)", "sar_filing (EU)"],
        "verdict": fs.get("final_verdict", "—"),
        "flagged": fs.get("transaction_frozen", False),
    },
]

for step in debate_steps:
    dot_color = RED if step["flagged"] else GREEN
    status    = pill("FLAGGED", True) if step["flagged"] else pill("CLEAR", False)
    tools_html = "".join([f'<span class="dtool">{t}</span>' for t in step["tools"]])
    verdict_preview = step["verdict"][:350] + ("…" if len(step["verdict"]) > 350 else "")
    st.markdown(f"""
    <div class="debate-step">
      <div class="ddot" style="background:{dot_color}"></div>
      <div class="dagent">{step['agent']} &nbsp; {status}</div>
      <div class="dtools">{tools_html}</div>
      <div class="dverdict">{verdict_preview}</div>
    </div>""", unsafe_allow_html=True)

hr()


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — SHAP + Cycle motif
# ─────────────────────────────────────────────────────────────────────────────

c_shap, c_cycle = st.columns([3, 2])

with c_shap:
    st.markdown('<span class="lbl">SHAP Feature Attributions</span>', unsafe_allow_html=True)
    attrs      = xai.attributions[:10]
    labels     = [a.human_label[:40] for a in attrs]
    values     = [a.shap_value for a in attrs]
    bar_colors = [RED if v > 0 else GREEN for v in values]

    fig_shap = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=bar_colors,
        text=[f"{v:+.3f}" for v in values],
        textposition="outside",
        textfont=dict(size=9, color=T_SEC, family="Inter"),
    ))
    fig_shap.update_layout(
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family="Inter", color=T_PRI, size=10),
        xaxis=dict(
            title="← safe  ·  risk →",
            titlefont=dict(size=9, color=T_FAINT),
            gridcolor=BORDER, zerolinecolor=BORDER,
            zeroline=True, zerolinewidth=1.5,
        ),
        yaxis=dict(autorange="reversed", gridcolor=BORDER),
        margin=dict(l=0, r=55, t=8, b=30),
        height=370,
    )
    st.plotly_chart(fig_shap, use_container_width=True)

with c_cycle:
    st.markdown('<span class="lbl">Cycle Motif Detection</span>', unsafe_allow_html=True)
    cycles = g.get("cycle_motifs_detected", [])
    if cycles:
        cycle  = cycles[0]
        path   = cycle["path"]
        n      = len(path) - 1
        node_x = [math.cos(2 * math.pi * i / n) for i in range(n)]
        node_y = [math.sin(2 * math.pi * i / n) for i in range(n)]
        edge_x, edge_y = [], []
        for i in range(n):
            j = (i + 1) % n
            edge_x += [node_x[i], node_x[j], None]
            edge_y += [node_y[i], node_y[j], None]

        fig_g = go.Figure()
        fig_g.add_trace(go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(width=1.5, color=BORDER), hoverinfo="none",
        ))
        fig_g.add_trace(go.Scatter(
            x=node_x, y=node_y, mode="markers+text",
            marker=dict(size=22, color=RED, line=dict(width=2.5, color=SURFACE)),
            text=[p.split("-")[-1] for p in path[:n]],
            textposition="top center",
            textfont=dict(size=8, color=T_SEC, family="IBM Plex Mono"),
            hovertext=path[:n], hoverinfo="text",
        ))
        fig_g.update_layout(
            paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
            showlegend=False, height=280,
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            margin=dict(l=20, r=20, t=10, b=10),
        )
        st.plotly_chart(fig_g, use_container_width=True)
        st.markdown(
            f"<div style='font-size:0.74rem;color:{T_FAINT}'>"
            f"<b style='color:{T_SEC}'>{cycle['cycle_id']}</b>"
            f" &nbsp;·&nbsp; {cycle['num_legs']} legs"
            f" &nbsp;·&nbsp; ${cycle['total_amount_usd']:,} total"
            f" &nbsp;·&nbsp; {cycle['time_span_hours']}h span"
            f" &nbsp;·&nbsp; smurfing variance {cycle['smurfing_variance']:.0%}"
            f"</div>", unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='color:{T_FAINT};font-size:0.85rem;padding-top:2rem'>"
            f"No cycle motifs detected.</div>", unsafe_allow_html=True,
        )

hr()


# ─────────────────────────────────────────────────────────────────────────────
# Section 6 — Regulatory Breach Table
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<span class="lbl">Regulatory Breach Summary</span>', unsafe_allow_html=True)
st.markdown(
    f"<div style='display:grid;grid-template-columns:11rem 5.5rem 1fr 11rem;gap:1rem;"
    f"padding:0.4rem 1rem;font-size:0.65rem;font-weight:600;letter-spacing:0.1em;"
    f"text-transform:uppercase;color:{T_FAINT}'>"
    f"<div>Rule ID</div><div>Status</div><div>Reason</div>"
    f"<div style='text-align:right'>Penalty</div></div>",
    unsafe_allow_html=True,
)
for r in xai.regulatory_links:
    status_html = (
        f'<div class="breach">● BREACH</div>'
        if r["breach"] else
        f'<div class="bclean">● COMPLIANT</div>'
    )
    st.markdown(f"""
    <div class="brow">
      <div class="brule">{r['rule_id']}</div>
      {status_html}
      <div class="breason">{r['reason']}</div>
      <div class="bpen">{r['penalty'][:55]}</div>
    </div>""", unsafe_allow_html=True)

hr()


# ─────────────────────────────────────────────────────────────────────────────
# Section 7 — Compliance KPIs Over Time
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<span class="lbl">Compliance KPIs Over Time</span>', unsafe_allow_html=True)

random.seed(42)
months = [(datetime.now() - timedelta(days=30*i)).strftime("%b %Y") for i in range(11, -1, -1)]

sars_m   = [random.randint(2, 14)            for _ in months]
fp_rate  = [round(random.uniform(0.08, 0.22), 2) for _ in months]
dec_time = [random.randint(280, 620)         for _ in months]
breaches = [random.randint(3, 18)            for _ in months]

# Pin current month to live run values
sars_m[-1]   = len(fs.get("sar_filings", []))
fp_rate[-1]  = round(1 - xai.model_confidence, 2)
dec_time[-1] = 412
breaches[-1] = sum(1 for r in xai.regulatory_links if r["breach"])

ck1, ck2 = st.columns(2)
ck3, ck4 = st.columns(2)

chart_layout = dict(
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    font=dict(family="Inter", color=T_PRI, size=9),
    margin=dict(l=10, r=10, t=40, b=50),
    height=250,
    showlegend=False,
)

with ck1:
    fig = go.Figure(go.Bar(
        x=months, y=sars_m,
        marker_color=[RED if i == len(months)-1 else "#E0E0E0" for i in range(len(months))],
        text=sars_m, textposition="outside", textfont=dict(size=9),
    ))
    fig.update_layout(**chart_layout,
        title=dict(text="SARs Filed per Month", font=dict(size=11), x=0),
        xaxis=dict(gridcolor=BORDER, tickangle=-40),
        yaxis=dict(gridcolor=BORDER, title="Count"),
    )
    st.plotly_chart(fig, use_container_width=True)

with ck2:
    fig = go.Figure(go.Scatter(
        x=months, y=fp_rate, mode="lines+markers",
        line=dict(color=BLUE, width=2),
        marker=dict(size=5, color=BLUE),
        fill="tozeroy", fillcolor="rgba(0,87,255,0.05)",
    ))
    fig.update_layout(**chart_layout,
        title=dict(text="False Positive Rate", font=dict(size=11), x=0),
        xaxis=dict(gridcolor=BORDER, tickangle=-40),
        yaxis=dict(gridcolor=BORDER, tickformat=".0%"),
    )
    st.plotly_chart(fig, use_container_width=True)

with ck3:
    fig = go.Figure(go.Scatter(
        x=months, y=dec_time, mode="lines+markers",
        line=dict(color=GREEN, width=2),
        marker=dict(size=5, color=GREEN),
    ))
    fig.update_layout(**chart_layout,
        title=dict(text="Avg Decision Time (ms)", font=dict(size=11), x=0),
        xaxis=dict(gridcolor=BORDER, tickangle=-40),
        yaxis=dict(gridcolor=BORDER, title="ms"),
    )
    st.plotly_chart(fig, use_container_width=True)

with ck4:
    fig = go.Figure(go.Bar(
        x=months, y=breaches,
        marker_color=[RED if i == len(months)-1 else "#E0E0E0" for i in range(len(months))],
        text=breaches, textposition="outside", textfont=dict(size=9),
    ))
    fig.update_layout(**chart_layout,
        title=dict(text="Regulatory Breaches Caught", font=dict(size=11), x=0),
        xaxis=dict(gridcolor=BORDER, tickangle=-40),
        yaxis=dict(gridcolor=BORDER, title="Count"),
    )
    st.plotly_chart(fig, use_container_width=True)

hr()


# ─────────────────────────────────────────────────────────────────────────────
# Section 8 — SAR Receipts + Reasoning Trace
# ─────────────────────────────────────────────────────────────────────────────

c_sar, c_trace = st.columns(2)

with c_sar:
    st.markdown('<span class="lbl">SAR / STR Filing Receipts</span>', unsafe_allow_html=True)
    sar_list = fs.get("sar_filings", [])
    if sar_list:
        for s in sar_list:
            st.markdown(f"""
            <div class="sarcard">
              <div style="font-size:0.82rem;font-weight:600">{s['jurisdiction']}</div>
              <div class="sarid">{s['tracking_id']}</div>
              <div class="sarmeta">Filed: {s['filed_at'][:19]} &nbsp;·&nbsp; Est. review: {s['estimated_review_days']} days</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='color:{T_FAINT};font-size:0.85rem'>No SARs filed.</div>",
                    unsafe_allow_html=True)

with c_trace:
    st.markdown('<span class="lbl">Reasoning Trace (LangSmith-style)</span>', unsafe_allow_html=True)
    trace_rows = [
        ("india_expert", "neo4j_query",           14),
        ("india_expert", "account_lookup",          8),
        ("india_expert", "pinecone_search (RBI)",  22),
        ("india_expert", "LLM verdict",           380),
        ("eu_expert",    "account_lookup (hops)",   9),
        ("eu_expert",    "pinecone_search (EU)",   19),
        ("eu_expert",    "LLM verdict",           390),
        ("auditor",      "sar_filing × 2",         38),
        ("auditor",      "LLM final ruling",       410),
        ("freeze",       "pipeline complete",        2),
    ]
    total_ms = sum(r[2] for r in trace_rows)
    for node, tool, ms in trace_rows:
        bar_w = max(4, int((ms / total_ms) * 100))
        bar_html = (
            f"<div style='display:inline-block;width:{bar_w}px;height:5px;"
            f"background:{BLUE};opacity:0.2;border-radius:2px;vertical-align:middle;"
            f"margin-right:6px'></div>"
        )
        st.markdown(f"""
        <div class="trow">
          <div class="tnode">{node}</div>
          <div class="ttool">{tool}</div>
          {bar_html}
          <div class="tms">{ms} ms</div>
        </div>""", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:0.72rem;color:{T_FAINT};margin-top:0.5rem;text-align:right'>"
        f"Total: {total_ms} ms</div>", unsafe_allow_html=True,
    )

hr()


# ─────────────────────────────────────────────────────────────────────────────
# Section 9 — LIME + PDF Download
# ─────────────────────────────────────────────────────────────────────────────

with st.expander("📄  LIME Local Explanation"):
    st.markdown(
        f"<div style='font-family:{MONO};font-size:0.8rem;line-height:1.7;"
        f"color:{T_SEC};background:{BG};border:1px solid {BORDER};"
        f"border-radius:6px;padding:0.9rem 1rem;white-space:pre-wrap'>"
        f"{xai.lime_summary}</div>",
        unsafe_allow_html=True,
    )

with st.expander("📥  Download PDF Audit Report"):
    st.markdown(
        f"<div style='font-size:0.82rem;color:{T_SEC};margin-bottom:0.7rem'>"
        f"Generates a 6-section legally defensible PDF — verdicts, breach table, "
        f"SHAP attributions, LIME narrative, and SAR receipts.</div>",
        unsafe_allow_html=True,
    )
    if st.button("Generate PDF"):
        from reports.report_generator import generate_report
        with st.spinner("Building PDF…"):
            _pdf_dir = os.path.join(_root, "output_reports")
            os.makedirs(_pdf_dir, exist_ok=True)
            out = generate_report(fs, xai, output_dir=_pdf_dir)
        with open(out, "rb") as f:
            st.download_button(
                label="⬇️  Download CCFA_Report.pdf",
                data=f,
                file_name=os.path.basename(out),
                mime="application/pdf",
            )

hr()
st.markdown(
    f"<div style='font-size:0.72rem;color:{T_FAINT};text-align:center'>"
    f"CCFA v2.0 &nbsp;·&nbsp; Phase 3: Multi-Agent Courtroom"
    f" &nbsp;·&nbsp; Phase 4: XAI Output"
    f" &nbsp;·&nbsp; Mock data — Phases 1 & 2 not connected"
    f"</div>",
    unsafe_allow_html=True,
)