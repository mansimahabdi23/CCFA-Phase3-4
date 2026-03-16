"""
dashboard.py
────────────
Phase 4 – Real-Time Compliance Dashboard (Streamlit).

Run with:
    streamlit run dashboard/dashboard.py

Shows:
  • Transaction summary card with risk level
  • GNN anomaly score + cycle motif graph
  • SHAP waterfall chart
  • Jurisdictional expert verdicts (collapsible)
  • Regulatory breach table
  • SAR filing status
  • LangSmith-style reasoning trace
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import time

# ── Try to import streamlit; if unavailable, print instructions ───────────
try:
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd
    STREAMLIT_OK = True
except ImportError:
    STREAMLIT_OK = False

if not STREAMLIT_OK:
    print(
        "Streamlit or Plotly not installed.\n"
        "Install with:\n"
        "    pip install streamlit plotly pandas\n"
        "Then run:\n"
        "    streamlit run dashboard/dashboard.py"
    )
    sys.exit(0)

# ── Import pipeline ────────────────────────────────────────────────────────
from agents.orchestrator import run_pipeline
from xai.xai_engine import explain

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CCFA — Compliance Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    .stApp { background-color: #0D1B2A; color: #ECF0F1; }
    .risk-badge-high {
        background: #C0392B; color: white; padding: 6px 18px;
        border-radius: 4px; font-weight: 700; font-size: 1.1rem;
        display: inline-block;
    }
    .risk-badge-low {
        background: #1E8449; color: white; padding: 6px 18px;
        border-radius: 4px; font-weight: 700; font-size: 1.1rem;
        display: inline-block;
    }
    .metric-card {
        background: #1A2C3D; border-left: 4px solid #D4AC0D;
        padding: 12px 16px; border-radius: 4px; margin-bottom: 8px;
    }
    .verdict-box {
        background: #1A2C3D; padding: 14px; border-radius: 6px;
        font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem;
        white-space: pre-wrap; line-height: 1.6;
    }
    .breach-tag  { color: #E74C3C; font-weight: 600; }
    .compliant-tag { color: #2ECC71; font-weight: 600; }
    .section-title {
        font-size: 1.05rem; font-weight: 700; color: #D4AC0D;
        letter-spacing: 0.08em; text-transform: uppercase;
        border-bottom: 1px solid #2C3E50; padding-bottom: 4px;
        margin-bottom: 12px;
    }
    [data-testid="stMetricValue"] { color: #D4AC0D !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://img.icons8.com/ios/80/D4AC0D/scales.png", width=60)
    st.markdown("## CCFA Dashboard")
    st.markdown("*Cognitive Compliance & Forensic Auditor*")
    # st.divider()
    # run_btn = st.button("▶  Run New Analysis", type="primary", use_container_width=True)
    st.divider()
    # st.markdown("**Phase 3** — Multi-Agent Courtroom  \n✓ IndiaExpert (RBI)  \n✓ EUExpert (AMLD-6)  \n✓ FinCENExpert (BSA)  \n✓ Auditor")
    # st.markdown("**Phase 4** — XAI Output  \n✓ SHAP Attributions  \n✓ LIME Explanation  \n✓ PDF Report  \n✓ SAR Filing")
    # st.divider()
    # st.caption("All data is hardcoded mock data for Phase 3/4 demo. Phases 1 & 2 not connected.")
    st.caption("CCFA v0.1.0-demo  |   Multi-Agent Courtroom  |   XAI Output  |  ")

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

if "final_state" not in st.session_state or run_btn:
    with st.spinner("Running Multi-Agent Courtroom pipeline..."):
        st.session_state.final_state = run_pipeline()
        st.session_state.xai_report  = explain(st.session_state.final_state)

fs  = st.session_state.final_state
xai = st.session_state.xai_report


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

col_title, col_badge = st.columns([5, 1])
with col_title:
    st.markdown(f"## Transaction `{fs['transaction']['id']}`")
    st.caption(f"Run ID: `{fs.get('run_id','—')}` | Completed: `{fs.get('completed_at','—')}`")
with col_badge:
    badge_class = "risk-badge-high" if xai.model_prediction == "HIGH RISK" else "risk-badge-low"
    st.markdown(
        f'<div style="margin-top:16px"><span class="{badge_class}">'
        f'{xai.model_prediction}</span></div>',
        unsafe_allow_html=True,
    )

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Row 1 — KPI Metrics
# ─────────────────────────────────────────────────────────────────────────────

c1, c2, c3, c4, c5 = st.columns(5)
txn = fs["transaction"]
g   = fs["graph_analysis"]

c1.metric("Amount",        f"${txn['amount_usd']:,.0f}")
c2.metric("GNN Anomaly",   f"{g['anomaly_score']:.2f}",   delta="HIGH" if g['anomaly_score'] > 0.75 else "LOW")
c3.metric("Shell Prob.",   f"{g['shell_company_probability']:.0%}")
c4.metric("Confidence",    f"{xai.model_confidence:.0%}")
c5.metric("SARs Filed",    str(len(fs.get("sar_filings", []))))


# ─────────────────────────────────────────────────────────────────────────────
# Row 2 — SHAP Waterfall  +  Cycle Detection
# ─────────────────────────────────────────────────────────────────────────────

col_shap, col_cycle = st.columns([3, 2])

with col_shap:
    st.markdown('<p class="section-title">SHAP Feature Attributions</p>', unsafe_allow_html=True)
    attrs  = xai.attributions[:10]
    labels = [a.human_label[:35] for a in attrs]
    values = [a.shap_value for a in attrs]
    colors_bar = ["#C0392B" if v > 0 else "#1E8449" for v in values]

    fig_shap = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=colors_bar,
        text=[f"{v:+.3f}" for v in values],
        textposition="outside",
    ))
    fig_shap.update_layout(
        paper_bgcolor="#0D1B2A",
        plot_bgcolor="#0D1B2A",
        font=dict(color="#ECF0F1", size=10),
        xaxis=dict(title="SHAP Value", gridcolor="#2C3E50", zerolinecolor="#D4AC0D"),
        yaxis=dict(autorange="reversed", gridcolor="#2C3E50"),
        margin=dict(l=10, r=40, t=10, b=30),
        height=360,
    )
    st.plotly_chart(fig_shap, use_container_width=True)

with col_cycle:
    st.markdown('<p class="section-title">Cycle Motif Detection</p>', unsafe_allow_html=True)
    cycles = g.get("cycle_motifs_detected", [])
    if cycles:
        cycle = cycles[0]
        path  = cycle["path"]
        n     = len(path) - 1   # last = first (closed loop)
        import math
        node_x = [math.cos(2*math.pi*i/n) for i in range(n)]
        node_y = [math.sin(2*math.pi*i/n) for i in range(n)]
        # edges
        edge_x, edge_y = [], []
        for i in range(n):
            j = (i+1) % n
            edge_x += [node_x[i], node_x[j], None]
            edge_y += [node_y[i], node_y[j], None]

        fig_graph = go.Figure()
        fig_graph.add_trace(go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(width=2, color="#D4AC0D"), hoverinfo="none"
        ))
        fig_graph.add_trace(go.Scatter(
            x=node_x, y=node_y, mode="markers+text",
            marker=dict(size=18, color="#C0392B", line=dict(width=2, color="#D4AC0D")),
            text=[p[:12] for p in path[:n]],
            textposition="top center",
            textfont=dict(size=8, color="#ECF0F1"),
            hovertext=path[:n], hoverinfo="text",
        ))
        fig_graph.update_layout(
            paper_bgcolor="#0D1B2A", plot_bgcolor="#1A2C3D",
            showlegend=False, height=280,
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig_graph, use_container_width=True)
        st.caption(
            f"**{cycle['cycle_id']}** — {cycle['num_legs']} legs, "
            f"${cycle['total_amount_usd']:,}, {cycle['time_span_hours']}h span. "
            f"Smurfing variance: {cycle['smurfing_variance']:.0%}"
        )
    else:
        st.info("No cycle motifs detected.")


# ─────────────────────────────────────────────────────────────────────────────
# Row 3 — Expert Verdicts
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
st.markdown('<p class="section-title">Jurisdictional Expert Verdicts</p>', unsafe_allow_html=True)

tab_india, tab_eu, tab_auditor = st.tabs([
    "🇮🇳  India (RBI)",
    "🇪🇺  EU (AMLD-6)",
    "⚖️  Auditor",
])
for tab, key in [
    (tab_india,   "india_expert_verdict"),
    (tab_eu,      "eu_expert_verdict"),
    (tab_auditor, "final_verdict"),
]:
    with tab:
        verdict_text = fs.get(key, "—")
        st.markdown(f'<div class="verdict-box">{verdict_text}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Row 4 — Regulatory Breaches
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
st.markdown('<p class="section-title">Regulatory Breach Summary</p>', unsafe_allow_html=True)

breach_rows = []
for r in xai.regulatory_links:
    breach_rows.append({
        "Rule ID":   r["rule_id"],
        "Status":    "BREACH" if r["breach"] else "COMPLIANT",
        "Reason":    r["reason"],
        "Penalty":   r["penalty"],
    })
df_breach = pd.DataFrame(breach_rows)

def color_status(val):
    if val == "BREACH":
        return "color: #E74C3C; font-weight: bold"
    return "color: #2ECC71; font-weight: bold"

styled = df_breach.style.applymap(color_status, subset=["Status"])
st.dataframe(styled, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# Row 5 — SAR Filings  +  LangSmith Trace
# ─────────────────────────────────────────────────────────────────────────────

col_sar, col_trace = st.columns(2)

with col_sar:
    st.markdown('<p class="section-title">SAR / STR Filing Receipts</p>', unsafe_allow_html=True)
    sar_list = fs.get("sar_filings", [])
    if sar_list:
        for s in sar_list:
            with st.container():
                st.markdown(f"""
                <div class="metric-card">
                  <b>{s['jurisdiction']}</b> &nbsp;|&nbsp; <code>{s['tracking_id']}</code><br/>
                  Filed: {s['filed_at']}<br/>
                  Est. review: {s['estimated_review_days']} days
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No SARs filed.")

with col_trace:
    st.markdown('<p class="section-title">Reasoning Trace (LangSmith-style)</p>', unsafe_allow_html=True)
    trace_steps = [
        {"step": "1. india_expert_node", "tool": "neo4j_query",     "latency_ms": 14},
        {"step": "1. india_expert_node", "tool": "account_lookup",  "latency_ms": 8},
        {"step": "1. india_expert_node", "tool": "pinecone_search", "latency_ms": 22},
        {"step": "1. india_expert_node", "tool": "LLM (mock)",      "latency_ms": 380},
        {"step": "2. eu_expert_node",    "tool": "account_lookup",  "latency_ms": 9},
        {"step": "2. eu_expert_node",    "tool": "pinecone_search", "latency_ms": 19},
        {"step": "2. eu_expert_node",    "tool": "LLM (mock)",      "latency_ms": 390},
        {"step": "3. auditor_node",      "tool": "sar_filing × 2",  "latency_ms": 40},
        {"step": "3. auditor_node",      "tool": "LLM (mock)",      "latency_ms": 410},
        {"step": "4. freeze_and_report", "tool": "—",               "latency_ms": 2},
    ]
    df_trace = pd.DataFrame(trace_steps)
    fig_trace = px.bar(
        df_trace, x="latency_ms", y="tool", orientation="h",
        color="step", text="latency_ms",
        color_discrete_sequence=px.colors.qualitative.Dark24,
    )
    fig_trace.update_layout(
        paper_bgcolor="#0D1B2A", plot_bgcolor="#1A2C3D",
        font=dict(color="#ECF0F1", size=9),
        xaxis=dict(title="Latency (ms)", gridcolor="#2C3E50"),
        yaxis=dict(title=""),
        legend=dict(font=dict(size=8), bgcolor="#1A2C3D"),
        margin=dict(l=10, r=30, t=10, b=30),
        height=360,
    )
    st.plotly_chart(fig_trace, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Row 6 — LIME Narrative + PDF Download
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
with st.expander("📄  LIME Local Explanation"):
    st.markdown(f'<div class="verdict-box">{xai.lime_summary}</div>', unsafe_allow_html=True)

with st.expander("📥  Download PDF Report"):
    st.markdown("Click to generate and download the full legally-defensible audit report.")
    if st.button("Generate PDF Report"):
        from reports.report_generator import generate_report
        import tempfile
        with st.spinner("Generating PDF..."):
            out_path = generate_report(fs, xai, output_dir="/tmp/ccfa_reports")
        with open(out_path, "rb") as f:
            st.download_button(
                label="⬇️  Download CCFA_Report.pdf",
                data=f,
                file_name=os.path.basename(out_path),
                mime="application/pdf",
            )

st.divider()
st.caption(
    "CCFA v0.1.0-demo  |  Phase 3: Multi-Agent Courtroom  |  Phase 4: XAI Output  |  "
)
